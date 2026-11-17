"""Giao diện ViMedWaste (Streamlit).

Chạy:  streamlit run demo/streamlit_app.py   (từ thư mục ViMedWaste, đã kích hoạt .venv)

- Có artifacts/models/vimedwaste.onnx → chạy mô hình thật (vimedwaste.serving.inference).
- Chưa có → CHẾ ĐỘ MINH HỌA: xác suất do người dùng chỉnh, logic quyết định vẫn là thật.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yaml
from PIL import Image

from vimedwaste.core.config import DEFAULT_CONFIG, load_config
from vimedwaste.core.paths import EXTERNAL_DIR, MODELS_DIR, RESULTS_DIR, ROOT
from vimedwaste.serving.decision import OK, UNKNOWN, WARN, bayes_thresholds, correct_bins, decide
from vimedwaste.serving.inference import MODEL_PATH, load_predictor

EXT_DIR = EXTERNAL_DIR / "mw40_v01"
META_PATH = MODELS_DIR / "meta.json"
TRAIN_RESULT = RESULTS_DIR / "train_mw40.json"

BIN_STYLE = {  # màu nền, viền, chữ
    "B1": ("#F2C94C", "#8A6D1B", "#14213D"),
    "B2": ("#F7DC6F", "#B8912A", "#14213D"),
    "B3": ("#2B2B2B", "#000000", "#F7F6F2"),
    "B4": ("#2F8A57", "#22673F", "#F7F6F2"),
    "B5": ("#F7F6F2", "#9AA3AF", "#14213D"),
}
PAGES = ["Kiểm tra thùng", "Dữ liệu", "Mô hình", "Tập nhãn & quy tắc"]

st.set_page_config(page_title="ViMedWaste", page_icon="🗑️", layout="wide")
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, button, input, select, textarea {
  font-family: 'Be Vietnam Pro', Arial, sans-serif !important; }
h1, h2, h3 { color: #14213D; }
.vm-banner { border-radius: 14px; padding: 16px 20px; margin: 4px 0 14px; border: 2px solid; }
.vm-banner .t { font-size: 22px; font-weight: 700; }
.vm-banner .s { font-size: 15px; margin-top: 4px; }
.vm-warn { background: #FBEBDD; border-color: #B45309; color: #5A2A07; }
.vm-warn .t { color: #8A3D07; }
.vm-ok { background: #E4F1EE; border-color: #0E6E62; color: #0A4B43; }
.vm-unk { background: #E8EAEE; border-color: #4B5563; color: #1F2937; }
.vm-demo { background: #FFF7D6; border: 1px solid #E0C25A; border-radius: 10px; padding: 8px 12px; font-size: 14px; }
.vm-row { display: grid; grid-template-columns: 52px 1fr 220px 60px 64px; gap: 10px; align-items: center;
  padding: 6px 4px; border-bottom: 1px solid #E5E7EB; font-size: 14px; }
.vm-row.head { font-weight: 600; color: #4B5563; }
.vm-row.on { background: #F3F8F7; }
.vm-row.bad { background: #FBEBDD; }
.vm-bar { position: relative; height: 12px; background: #ECEFF3; border-radius: 6px; }
.vm-bar .f { position: absolute; left: 0; top: 0; bottom: 0; background: #0E6E62; border-radius: 6px; }
.vm-bar.bad .f { background: #B45309; }
.vm-bar .t { position: absolute; top: -4px; bottom: -4px; width: 2px; background: #14213D; }
.vm-chip { display: inline-block; width: 18px; height: 18px; border-radius: 4px; border: 2px solid;
  vertical-align: middle; margin-right: 6px; }
.vm-viol { background: #FFFFFF; border-radius: 10px; padding: 8px 12px; margin: 6px 0; border-left: 4px solid #B45309; }
</style>
""",
    unsafe_allow_html=True,
)


# ---------- dữ liệu và mô hình (có cache) ----------

def _mtime(p: Path) -> float:
    return p.stat().st_mtime if p.exists() else 0.0


@st.cache_data(show_spinner=False)
def _raw_config(_mt: float) -> dict:
    return yaml.safe_load(DEFAULT_CONFIG.read_text(encoding="utf-8"))


@st.cache_data(show_spinner=False)
def _read_csv(path: str, _mt: float) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"image_id": str, "image_id_a": str, "image_id_b": str})


def table(name: str) -> pd.DataFrame | None:
    p = EXT_DIR / f"{name}.csv"
    return _read_csv(str(p), _mtime(p)) if p.exists() else None


@st.cache_data(show_spinner=False, max_entries=600)
def thumbnail(path: str, size: int, _mt: float) -> Image.Image:
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((size, size))
        return im.copy()


def thumb(rel_path: str, size: int = 320) -> Image.Image | None:
    p = (ROOT / rel_path).resolve()
    return thumbnail(str(p), size, _mtime(p)) if p.exists() else None


@st.cache_resource(show_spinner="Đang nạp mô hình…")
def _predictor(_mt: float):
    return load_predictor()


def predictor():
    return _predictor(_mtime(MODEL_PATH))


def model_meta() -> dict | None:
    if not META_PATH.exists():
        return None
    try:
        return json.loads(META_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


@st.cache_data(show_spinner=False)
def dataset_index(_mt: float) -> pd.DataFrame | None:
    """metadata + nhãn thật + tập (train/val/OOD) cho mọi ảnh đã nhập."""
    meta, labels, splits = table("metadata"), table("labels"), table("splits")
    if meta is None:
        return None
    cfg = load_config()
    df = meta[["image_id", "file_path", "source_class", "is_ood"]].copy()
    df["is_ood"] = df.is_ood.astype(str).str.lower() == "true"
    if splits is not None:
        df = df.merge(splits[["image_id", "split"]], on="image_id", how="left")
    else:
        df["split"] = None
    df.loc[df.is_ood, "split"] = "OOD"
    if labels is not None:
        lab = labels.set_index("image_id")[cfg.labels]
        df["true_labels"] = df.image_id.map(lambda i: [k for k in cfg.labels if i in lab.index and lab.at[i, k] == 1])
    else:
        df["true_labels"] = [[] for _ in range(len(df))]
    return df.sort_values(["source_class", "file_path"]).reset_index(drop=True)


def index_df() -> pd.DataFrame | None:
    return dataset_index(_mtime(EXT_DIR / "metadata.csv") + _mtime(EXT_DIR / "splits.csv"))


# ---------- thành phần hiển thị ----------

def bin_label(b: str, names: dict) -> str:
    return f"{b} · {names.get(b, '')}"


def chip(b: str) -> str:
    bg, border, _ = BIN_STYLE[b]
    return f'<span class="vm-chip" style="background:{bg};border-color:{border}"></span>'


def banner(d, names: dict, bins: dict) -> str:
    if d.status == UNKNOWN:
        return ('<div class="vm-banner vm-unk"><div class="t">KHÔNG XÁC ĐỊNH</div>'
                f'<div class="s">Ảnh khác xa dữ liệu đã học (điểm lớp mở {d.ood_score:.2f} &lt; τ = {d.tau:.2f}). '
                'Hệ thống không đưa nhãn để tránh đoán bừa: chụp lại hoặc kiểm tra thủ công.</div></div>')
    if d.status == WARN:
        return ('<div class="vm-banner vm-warn"><div class="t">CẢNH BÁO: bỏ sai thùng</div>'
                f'<div class="s">{len(d.violations)} loại chất thải không được bỏ vào '
                f'{html.escape(bin_label(d.bin_id, bins))}.</div></div>')
    found = ", ".join(f"{k} {names[k]}" for k in d.present) or "không phát hiện nhãn nào vượt ngưỡng"
    return ('<div class="vm-banner vm-ok"><div class="t">PHÙ HỢP</div>'
            f'<div class="s">Thùng {html.escape(bin_label(d.bin_id, bins))} · {html.escape(found)}</div></div>')


def label_table(d, names: dict) -> str:
    rows = ['<div class="vm-row head"><div>Mã</div><div>Nhãn</div><div>Xác suất · vạch = ngưỡng</div>'
            '<div>p</div><div>Có mặt</div></div>']
    for k in load_config().labels:
        p, t = d.probs[k], d.thresholds[k]
        bad = k in d.violations
        on = k in d.present
        cls = "bad" if bad else ("on" if on else "")
        rows.append(
            f'<div class="vm-row {cls}"><div><b>{k}</b></div><div>{html.escape(names[k])}</div>'
            f'<div class="vm-bar {"bad" if bad else ""}"><div class="f" style="width:{p * 100:.1f}%"></div>'
            f'<div class="t" style="left:{t * 100:.1f}%"></div></div>'
            f'<div>{p:.2f}</div><div>{"Có" if on else "–"}</div></div>'
        )
    return "".join(rows)


# ---------- các trang ----------

def page_check(cfg, raw):
    names = cfg.names
    bins = raw["bins"]
    pred = predictor()
    meta = model_meta() if pred else None

    st.title("Kiểm tra thùng")
    if pred is None:
        st.markdown('<div class="vm-demo"><b>Chế độ minh họa:</b> chưa có mô hình (artifacts/models/vimedwaste.onnx). '
                    'Xác suất bên dưới là <b>giả lập</b> do bạn chỉnh; logic ngưỡng và cảnh báo là thật.</div>',
                    unsafe_allow_html=True)
    elif meta and meta.get("warning"):
        st.warning(meta["warning"])

    with st.sidebar:
        st.subheader("Ảnh")
        source = st.radio("Nguồn ảnh", ["Medical Waste 4.0", "Tải ảnh lên"], key="src", horizontal=True)
        image, truth, img_key, true_list = None, None, None, []
        if source == "Tải ảnh lên":
            up = st.file_uploader("Chọn ảnh (jpg, png)", type=["jpg", "jpeg", "png"], key="upload")
            if up is not None:
                image = Image.open(up).convert("RGB")
                img_key = f"up_{up.name}_{up.size}"
        else:
            idx = index_df()
            if idx is None:
                st.info("Chưa nhập Medical Waste 4.0 (chạy vimedwaste.data.import_mw40).")
            else:
                classes = sorted(idx.source_class.unique())
                cls = st.selectbox("Lớp gốc", classes, key="cls")
                splits = sorted(idx[idx.source_class == cls].split.dropna().unique())
                sp = st.selectbox("Tập", splits, key="split")
                sub = idx[(idx.source_class == cls) & (idx.split == sp)].reset_index(drop=True)
                i = st.number_input(f"Ảnh số (1–{len(sub)})", 1, max(len(sub), 1), 1, key="img_i") - 1
                row = sub.iloc[int(i)]
                full = (ROOT / row.file_path).resolve()
                if full.exists():
                    image = thumb(row.file_path, 1024)
                    img_key = row.image_id
                    true_list = list(row.true_labels)
                    truth = "OOD gần (vật y tế ngoài 10 nhãn)" if row.is_ood else (
                        ", ".join(f"{k} {names[k]}" for k in row.true_labels) or "không có nhãn")
                else:
                    st.error(f"Không thấy file ảnh: {row.file_path}")

        st.subheader("Thùng đang dùng")
        bin_id = st.radio("Loại thùng", cfg.bins, index=3, key="bin",
                          format_func=lambda b: bin_label(b, bins))
        st.markdown(chip(bin_id) + html.escape(bin_label(bin_id, bins)), unsafe_allow_html=True)

    if image is None:
        st.info("Chọn hoặc tải một ảnh ở thanh bên trái.")
        return

    thresholds = bayes_thresholds(cfg)
    ood_score, tau = None, None
    if pred is not None:
        probs, ood_score = pred.predict(image)
        tau = (meta or {}).get("tau")
    else:
        with st.expander("Xác suất giả lập (chưa có mô hình)", expanded=True):
            sim_ood = st.checkbox("Giả lập vật lạ (điểm lớp mở dưới ngưỡng τ)", key=f"ood_{img_key}")
            cols = st.columns(5)
            probs = {}
            for j, k in enumerate(cfg.labels):
                default = 0.85 if k in true_list else 0.03
                probs[k] = cols[j % 5].slider(k, 0.0, 1.0, float(default), 0.01, key=f"p_{k}_{img_key}",
                                              help=names[k])
            if sim_ood:
                ood_score, tau = 0.0, 1.0

    d = decide(probs, bin_id, thresholds=thresholds, ood_score=ood_score, tau=tau, cfg=cfg)

    left, right = st.columns([5, 7], gap="large")
    with left:
        st.image(image, width="stretch")
        if truth:
            st.caption(f"Nhãn thật (từ bộ dữ liệu): {truth}")
        if ood_score is not None and tau is not None and pred is not None:
            st.caption(f"Điểm lớp mở JointEnergy = {ood_score:.2f} · τ = {tau:.2f} "
                       f"({'chấp nhận' if ood_score >= tau else 'từ chối'})")
    with right:
        st.markdown(banner(d, names, bins), unsafe_allow_html=True)
        for k in d.violations:
            ok_bins = ", ".join(bin_label(b, bins) for b in correct_bins(k, cfg))
            st.markdown(f'<div class="vm-viol"><b>{k}</b> {html.escape(names[k])} · p = {probs[k]:.2f}<br>'
                        f'→ bỏ vào: {html.escape(ok_bins)}</div>', unsafe_allow_html=True)
        if d.status != UNKNOWN:
            st.markdown(label_table(d, names), unsafe_allow_html=True)
            st.caption("Ngưỡng theo quy tắc Bayes t_k = C_FP / (C_FP + C_FN,k): "
                       "0,09 cho vật sắc nhọn, 0,17 cho lây nhiễm và nguy hại, 0,50 cho tái chế và thông thường.")


def page_data(cfg):
    st.title("Dữ liệu")
    man, meta, labels, splits = table("manifest"), table("metadata"), table("labels"), table("splits")
    if man is None or meta is None:
        st.info("Chưa có dữ liệu. Chạy: python -m vimedwaste.data.import_mw40 --src \"../Medical Waste 4.0\"")
        return
    st.caption("Nguồn: Medical Waste 4.0 v0.1 (Zenodo 7643417, CC BY 4.0). Dữ liệu ngoài: chỉ để chạy thử và pretrain, "
               "không vào tập test, không tính vào 2.500 ảnh.")
    status = man.status.value_counts()
    c = st.columns(5)
    c[0].metric("Ảnh RGB gốc", f"{len(man):,}".replace(",", "."))
    c[1].metric("Đã nhập", f"{len(meta):,}".replace(",", "."))
    c[2].metric("Có nhãn", f"{int(status.get('used', 0)):,}".replace(",", "."))
    c[3].metric("OOD gần", f"{int(status.get('ood', 0)):,}".replace(",", "."))
    c[4].metric("Bỏ (test_tube)", f"{int(status.get('skipped', 0)):,}".replace(",", "."))

    tab_stat, tab_gal, tab_dup, tab_val = st.tabs(["Thống kê", "Thư viện ảnh", "Ảnh gần trùng", "Kiểm tra ràng buộc"])

    with tab_stat:
        if labels is not None and splits is not None:
            active = [k for k in cfg.labels if labels[k].sum() > 0]
            m = labels.merge(splits, on="image_id")
            counts = m.groupby("split")[active].sum().T
            counts.index = [f"{k} {cfg.names[k]}" for k in counts.index]
            st.subheader("Số ảnh theo nhãn và tập")
            st.bar_chart(counts, stack=False, horizontal=True)
            st.dataframe(counts, width="stretch")
        st.subheader("Số ảnh theo lớp gốc")
        per = man.groupby(["source_class", "mapped_to", "status"], dropna=False).size().reset_index(name="số ảnh")
        st.dataframe(per, width="stretch", hide_index=True)

    with tab_gal:
        idx = index_df()
        f1, f2, f3 = st.columns(3)
        cls = f1.selectbox("Lớp gốc", ["(tất cả)", *sorted(idx.source_class.unique())], key="g_cls")
        sp = f2.selectbox("Tập", ["(tất cả)", *sorted(idx.split.dropna().unique())], key="g_split")
        sub = idx
        if cls != "(tất cả)":
            sub = sub[sub.source_class == cls]
        if sp != "(tất cả)":
            sub = sub[sub.split == sp]
        per_page = 12
        pages = max(1, -(-len(sub) // per_page))
        page = f3.number_input(f"Trang (1–{pages})", 1, pages, 1, key="g_page")
        st.caption(f"{len(sub)} ảnh")
        chunk = sub.iloc[(page - 1) * per_page: page * per_page]
        cols = st.columns(4)
        for j, row in enumerate(chunk.itertuples()):
            im = thumb(row.file_path, 320)
            with cols[j % 4]:
                if im is not None:
                    st.image(im, width="stretch")
                lab = "OOD gần" if row.is_ood else " ".join(row.true_labels)
                st.caption(f"{row.source_class} · {row.split} · {lab}")

    with tab_dup:
        nd = table("near_duplicates")
        if nd is None or nd.empty:
            st.info("Chưa có kết quả lọc trùng. Chạy vimedwaste.data.dedup với --splits.")
        else:
            has_split = {"split_a", "split_b"} <= set(nd.columns)
            cross_only = st.checkbox("Chỉ cặp vắt qua hai tập khác nhau (rò rỉ)", value=has_split, key="d_cross",
                                     disabled=not has_split)
            view = nd
            if cross_only and has_split:
                view = nd.dropna(subset=["split_a", "split_b"])
                view = view[view.split_a != view.split_b]
            st.caption(f"{len(view)} cặp (trên tổng {len(nd)} cặp gần trùng, Hamming ≤ ngưỡng phash)")
            if len(view):
                k = st.number_input(f"Cặp số (1–{len(view)})", 1, len(view), 1, key="d_i") - 1
                pair = view.iloc[int(k)]
                paths = meta.set_index("image_id").file_path
                a, b = st.columns(2)
                for col, iid, spl in ((a, pair.image_id_a, pair.get("split_a")), (b, pair.image_id_b, pair.get("split_b"))):
                    with col:
                        im = thumb(paths.get(iid, ""), 480) if iid in paths.index else None
                        if im is not None:
                            st.image(im, width="stretch")
                        st.caption(f"{iid[:10]}… · tập: {spl if isinstance(spl, str) else '–'}")
                st.markdown(f"Khoảng cách Hamming: **{int(pair.distance)}**")
                st.dataframe(view, width="stretch", hide_index=True, height=240)

    with tab_val:
        st.write("Kiểm tra mọi ràng buộc lược đồ của bảng dữ liệu ngoài (cột, giá trị, file ảnh, rò rỉ nhóm).")
        if st.button("Chạy kiểm tra", key="v_run"):
            from vimedwaste.data.validate_metadata import validate
            errs = validate(EXT_DIR, ROOT)
            if errs:
                st.error("KHÔNG ĐẠT")
                for e in errs:
                    st.write("- " + e)
            else:
                st.success(f"ĐẠT: {EXT_DIR.relative_to(ROOT).as_posix()} thỏa mọi ràng buộc.")


def _records_table(obj):
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        return pd.DataFrame(obj)
    if isinstance(obj, dict) and obj and all(isinstance(v, dict) for v in obj.values()):
        return pd.DataFrame(obj).T
    return None


def page_model():
    st.title("Mô hình")
    meta = model_meta()
    has_model = MODEL_PATH.exists()
    if not has_model and meta is None and not TRAIN_RESULT.exists():
        st.info("Chưa có mô hình. Khi huấn luyện xong sẽ có artifacts/models/vimedwaste.onnx, artifacts/models/meta.json "
                "và artifacts/results/train_mw40.json; trang này tự hiển thị.")
        return
    if meta and meta.get("warning"):
        st.warning(meta["warning"])
    c = st.columns(4)
    c[0].metric("File ONNX", "có" if has_model else "chưa có")
    if meta:
        if meta.get("temperature") is not None:
            c[1].metric("Nhiệt độ T", f"{meta['temperature']:.3f}")
        if meta.get("tau") is not None:
            c[2].metric("Ngưỡng lớp mở τ", f"{meta['tau']:.3f}")
        c[3].metric("Huấn luyện trên", str(meta.get("trained_on", "–")))
        if meta.get("trained_labels"):
            st.caption("Nhãn mô hình đã học: " + ", ".join(meta["trained_labels"]))
        metrics = meta.get("metrics")
        if metrics:
            st.subheader("Chỉ số (meta.json)")
            tbl = _records_table(metrics)
            st.dataframe(tbl, width="stretch") if tbl is not None else st.json(metrics)
    if TRAIN_RESULT.exists():
        res = json.loads(TRAIN_RESULT.read_text(encoding="utf-8"))
        st.subheader("Kết quả huấn luyện (artifacts/results/train_mw40.json)")
        shown = False
        for key, val in res.items():
            tbl = _records_table(val)
            if tbl is not None:
                st.markdown(f"**{key}**")
                st.dataframe(tbl, width="stretch")
                shown = True
        with st.expander("Toàn bộ JSON", expanded=not shown):
            st.json(res)


def page_rules(cfg, raw):
    st.title("Tập nhãn & quy tắc")
    t = bayes_thresholds(cfg)
    lab = pd.DataFrame([
        {"Mã": k, "Nhãn": cfg.names[k], "Nhóm": raw["labels"][k]["group"], "C_FN": cfg.c_fn[k],
         "Ngưỡng Bayes": round(t[k], 3), "Thùng đúng": ", ".join(correct_bins(k, cfg))}
        for k in cfg.labels
    ])
    st.dataframe(lab, width="stretch", hide_index=True)
    st.subheader("Ma trận tương thích A[k, b]")
    mat = pd.DataFrame(cfg.A, index=cfg.labels, columns=cfg.bins).replace({1: "✓", 0: "–"})
    mat.columns = [bin_label(b, raw["bins"]) for b in cfg.bins]
    st.dataframe(mat, width="stretch")
    st.caption("Cảnh báo khi ảnh có nhãn k vượt ngưỡng mà ô (k, thùng đang dùng) là “–”. "
               "C_FP = 1 cho mọi nhãn; ngưỡng t_k = C_FP / (C_FP + C_FN,k).")


def main():
    cfg = load_config()
    raw = _raw_config(_mtime(DEFAULT_CONFIG))
    with st.sidebar:
        st.markdown("### ViMedWaste")
        page = st.radio("Trang", PAGES, key="page")
        mode = "Mô hình ONNX" if MODEL_PATH.exists() else "Minh họa (chưa có mô hình)"
        st.caption(f"Chế độ: {mode}")
    if page == PAGES[0]:
        page_check(cfg, raw)
    elif page == PAGES[1]:
        page_data(cfg)
    elif page == PAGES[2]:
        page_model()
    else:
        page_rules(cfg, raw)


main()
