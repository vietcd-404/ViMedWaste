"""Chạy thử bước 3–5 trên Medical Waste 4.0: baseline cổ điển, mô hình chính, lớp mở, xuất ONNX.

CẢNH BÁO: dữ liệu ngoài chỉ có 3/10 nhãn (L03, L04, L05); mỗi lớp được chụp trong một phiên ngắn,
val nằm cùng phiên với train (chia theo khối thời gian) → điểm val cao ảo. Kết quả chỉ chứng minh
code huấn luyện chạy được, KHÔNG phải bằng chứng cho giả thuyết H1–H4.

  Bước 3 – baseline: mức sàn tần suất, Logistic, LinearSVC, KNN, RandomForest trên đặc trưng
           EfficientNet-B0 đóng băng (binary relevance).
  Bước 4 – mô hình chính: Linear(1280, 10) + BCE, AdamW weight decay 1e-4, dừng sớm theo mAP val,
           3 seed; temperature scaling một T chung.
  Bước 5 – lớp mở: JointEnergy, τ giữ 95 % val; AUROC trên 429 ảnh OOD gần.
  Xuất ONNX: backbone + đầu tuyến tính + chia T → artifacts/models/vimedwaste.onnx (+ meta.json).

Ví dụ:
  python -m vimedwaste.training.train_mw40
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler, normalize
from sklearn.svm import LinearSVC
from torch import nn

from ..core.config import load_config
from ..core.paths import EXTERNAL_DIR, FEATURES_DIR, MODELS_DIR, ROOT
from ..serving.decision import bayes_thresholds
from ..serving.inference import preprocess
from ..core.utils import git_commit, read_csv, write_result

DATA = EXTERNAL_DIR / "mw40_v01"
FEATURES = FEATURES_DIR / "mw40_effb0.npz"
MODELS = MODELS_DIR
ACTIVE = ["L03", "L04", "L05"]
WARNING = ("Chỉ huấn luyện trên Medical Waste 4.0: 3/10 nhãn, mỗi lớp chụp trong một phiên → "
           "điểm val cao ảo; chỉ để chạy thử, không phải bằng chứng")


# ---------- dữ liệu và đặc trưng ----------

def load_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Trả về (bảng trong phân phối có nhãn + split, bảng OOD gần)."""
    meta = read_csv(DATA / "metadata.csv")
    labels = read_csv(DATA / "labels.csv")
    splits = read_csv(DATA / "splits.csv")
    ind = labels.merge(splits[["image_id", "split"]], on="image_id").merge(
        meta[["image_id", "file_path"]], on="image_id")
    ood = meta[meta.is_ood.astype(str).str.lower() == "true"][["image_id", "file_path"]]
    return ind.reset_index(drop=True), ood.reset_index(drop=True)


def build_backbone() -> nn.Module:
    from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

    model = efficientnet_b0(weights=EfficientNet_B0_Weights.IMAGENET1K_V1)
    model.classifier = nn.Identity()   # đầu ra 1280 chiều sau avgpool
    return model.eval()


@torch.no_grad()
def extract(backbone: nn.Module, paths: list[str], batch: int = 16) -> np.ndarray:
    out = []
    for i in range(0, len(paths), batch):
        x = np.concatenate([preprocess(Image.open(ROOT / p)) for p in paths[i:i + batch]])
        out.append(backbone(torch.from_numpy(x)).numpy())
        print(f"  đặc trưng {min(i + batch, len(paths))}/{len(paths)}", end="\r")
    print()
    return np.concatenate(out).astype(np.float32)


def get_features(ind: pd.DataFrame, ood: pd.DataFrame, backbone: nn.Module) -> tuple[np.ndarray, np.ndarray]:
    ids = np.array(list(ind.image_id) + list(ood.image_id))
    if FEATURES.exists():
        cache = np.load(FEATURES, allow_pickle=False)
        if np.array_equal(cache["ids"], ids):
            print(f"Dùng đặc trưng đã lưu: {FEATURES}")
            return cache["x_ind"], cache["x_ood"]
    print("Trích đặc trưng EfficientNet-B0 (đóng băng)…")
    x_ind = extract(backbone, list(ind.file_path))
    x_ood = extract(backbone, list(ood.file_path))
    FEATURES.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(FEATURES, ids=ids, x_ind=x_ind, x_ood=x_ood)
    return x_ind, x_ood


# ---------- độ đo ----------

def metrics(y: np.ndarray, score: np.ndarray, pred: np.ndarray) -> dict:
    """y, score, pred: (N, 3) trên các nhãn ACTIVE."""
    ap = {k: float(average_precision_score(y[:, i], score[:, i])) for i, k in enumerate(ACTIVE)}
    return {
        "ap": ap,
        "mAP": float(np.mean(list(ap.values()))),
        "macro_f1": float(f1_score(y, pred, average="macro", zero_division=0)),
        "exact_match": float((y == pred).all(axis=1).mean()),
    }


def joint_energy(z: np.ndarray) -> np.ndarray:
    """S(x) = Σ_k log(1 + exp(z_k)); z là logit đã chia T. S cao = giống dữ liệu huấn luyện."""
    return np.logaddexp(0.0, z).sum(axis=1)


# ---------- bước 3: baseline cổ điển ----------

def run_baselines(xtr, ytr, xva, yva, thr_active) -> dict:
    results = {}
    prev = ytr.mean(axis=0)
    score = np.tile(prev, (len(yva), 1))
    results["muc_san_tan_suat"] = metrics(yva, score, (score >= thr_active).astype(int))

    scaler = StandardScaler().fit(xtr)
    s_tr, s_va = scaler.transform(xtr), scaler.transform(xva)
    n_tr, n_va = normalize(xtr), normalize(xva)

    def per_label(make, a_tr, a_va, kind):
        score = np.zeros_like(yva, dtype=float)
        for i in range(len(ACTIVE)):
            clf = make().fit(a_tr, ytr[:, i])
            score[:, i] = clf.decision_function(a_va) if kind == "margin" else clf.predict_proba(a_va)[:, 1]
        pred = (score >= 0).astype(int) if kind == "margin" else (score >= thr_active).astype(int)
        return metrics(yva, score, pred)

    results["logistic_regression"] = per_label(lambda: LogisticRegression(max_iter=3000, C=1.0), s_tr, s_va, "proba")
    results["linear_svc"] = per_label(lambda: LinearSVC(C=0.1, max_iter=5000), s_tr, s_va, "margin")
    results["knn_k5"] = per_label(lambda: KNeighborsClassifier(n_neighbors=5), n_tr, n_va, "proba")
    results["random_forest"] = per_label(
        lambda: RandomForestClassifier(n_estimators=300, random_state=0, n_jobs=-1), xtr, xva, "proba")
    return results


# ---------- bước 4: mô hình chính ----------

def train_head(xtr, ytr, xva, yva, seed: int, active_idx, max_epochs=300, patience=10):
    torch.manual_seed(seed)
    np.random.seed(seed)
    head = nn.Linear(xtr.shape[1], ytr.shape[1])
    opt = torch.optim.AdamW(head.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.BCEWithLogitsLoss()
    Xtr, Ytr, Xva = map(torch.from_numpy, (xtr, ytr.astype(np.float32), xva))
    best, best_state, wait, epoch = -1.0, None, 0, 0
    for epoch in range(1, max_epochs + 1):
        head.train()
        for idx in torch.randperm(len(Xtr)).split(64):
            opt.zero_grad()
            loss_fn(head(Xtr[idx]), Ytr[idx]).backward()
            opt.step()
        head.eval()
        with torch.no_grad():
            z = head(Xva).numpy()
        m = np.mean([average_precision_score(yva[:, j], z[:, j]) for j in active_idx])
        if m > best + 1e-6:
            best, wait = m, 0
            best_state = {k: v.clone() for k, v in head.state_dict().items()}
        else:
            wait += 1
            if wait >= patience:
                break
    head.load_state_dict(best_state)
    return head, float(best), epoch


def fit_temperature(z: np.ndarray, y: np.ndarray) -> float:
    """Một T chung, cực tiểu NLL nhị phân trên val (06 mục 4.7)."""
    Z, Y = torch.from_numpy(z.astype(np.float32)), torch.from_numpy(y.astype(np.float32))
    log_t = torch.zeros(1, requires_grad=True)
    opt = torch.optim.LBFGS([log_t], lr=0.1, max_iter=200)
    loss_fn = nn.BCEWithLogitsLoss()

    def closure():
        opt.zero_grad()
        loss = loss_fn(Z / log_t.exp(), Y)
        loss.backward()
        return loss

    opt.step(closure)
    return float(log_t.exp().item())


# ---------- xuất ONNX ----------

class FullModel(nn.Module):
    def __init__(self, backbone: nn.Module, head: nn.Linear, temperature: float):
        super().__init__()
        self.backbone, self.head = backbone, head
        self.register_buffer("t", torch.tensor(float(temperature)))

    def forward(self, image):
        return self.head(self.backbone(image)) / self.t


def export_onnx(model: FullModel, path: Path, sample: np.ndarray) -> float:
    import onnxruntime as ort

    path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()
    x = torch.from_numpy(sample)
    torch.onnx.export(model, (x,), str(path), input_names=["image"], output_names=["logits"],
                      dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
                      opset_version=17, dynamo=False)
    with torch.no_grad():
        ref = model(x).numpy()
    sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    got = sess.run(None, {"image": sample})[0]
    return float(np.abs(ref - got).max())


# ---------- chạy ----------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    args = ap.parse_args()
    t0 = time.time()

    cfg = load_config()
    labels = cfg.labels
    active_idx = [labels.index(k) for k in ACTIVE]
    thr = bayes_thresholds(cfg)
    thr_vec = np.array([thr[k] for k in labels])

    ind, ood = load_tables()
    backbone = build_backbone()
    x_ind, x_ood = get_features(ind, ood, backbone)
    Y = ind[labels].to_numpy().astype(int)
    tr, va = (ind.split == "train").to_numpy(), (ind.split == "val").to_numpy()
    xtr, xva, ytr, yva = x_ind[tr], x_ind[va], Y[tr], Y[va]
    print(f"train {tr.sum()} · val {va.sum()} · OOD gần {len(x_ood)}")

    # Bước 3
    baselines = run_baselines(xtr, ytr[:, active_idx], xva, yva[:, active_idx], thr_vec[active_idx])

    # Bước 4
    runs = []
    for seed in args.seeds:
        head, best_map, epochs = train_head(xtr, ytr, xva, yva, seed, active_idx)
        with torch.no_grad():
            z = head(torch.from_numpy(xva)).numpy()
        runs.append({"seed": seed, "head": head, "z_val": z, "val_mAP": best_map, "epochs": epochs})
        print(f"  seed {seed}: mAP val {best_map:.4f} sau {epochs} epoch")
    maps = np.array([r["val_mAP"] for r in runs])
    best_run = max(runs, key=lambda r: r["val_mAP"])
    T = fit_temperature(best_run["z_val"], yva)
    zt = best_run["z_val"] / T
    probs = 1 / (1 + np.exp(-zt))
    pred = (probs >= thr_vec).astype(int)
    head_metrics = metrics(yva[:, active_idx], probs[:, active_idx], pred[:, active_idx])
    false_alarm_other = float(pred[:, [i for i in range(len(labels)) if i not in active_idx]].any(axis=1).mean())

    # Bước 5 – lớp mở
    head = best_run["head"]
    with torch.no_grad():
        z_ood = head(torch.from_numpy(x_ood)).numpy() / T
    s_val, s_ood = joint_energy(zt), joint_energy(z_ood)
    tau = float(np.quantile(s_val, 0.05))
    auroc = float(roc_auc_score(np.r_[np.ones(len(s_val)), np.zeros(len(s_ood))], np.r_[s_val, s_ood]))
    fpr_at_tau = float((s_ood >= tau).mean())

    # Xuất ONNX
    sample = np.concatenate([preprocess(Image.open(ROOT / p)) for p in ind.file_path[va].head(4)])
    onnx_path = MODELS / "vimedwaste.onnx"
    max_diff = export_onnx(FullModel(backbone, head, T), onnx_path, sample)
    # Trọng số đầu tuyến tính + T cho Grad-CAM ở backend (backbone lấy lại từ torchvision).
    torch.save({"state_dict": head.state_dict(), "temperature": T}, MODELS / "head.pt")

    model_metrics = {
        "val_mAP_3_seed": {"mean": float(maps.mean()), "std": float(maps.std(ddof=0)), "per_seed": maps.tolist()},
        "best_seed": best_run["seed"],
        "best_seed_val_after_T": head_metrics,
        "val_rate_any_untrained_label_flagged": false_alarm_other,
        "temperature": T,
        "temperature_note": "T fit trên chính val (không có test riêng) → lạc quan",
        "open_set": {"score": "joint_energy", "tau_keep_95pct_val": tau, "auroc_val_vs_ood_near": auroc,
                     "ood_accepted_rate_at_tau": fpr_at_tau, "n_val": int(len(s_val)), "n_ood": int(len(s_ood))},
        "onnx_max_abs_diff": max_diff,
    }
    payload = {
        "warning": WARNING,
        "data": {"n_train": int(tr.sum()), "n_val": int(va.sum()), "n_ood_near": int(len(x_ood)),
                 "positives_train": dict(zip(ACTIVE, ytr[:, active_idx].sum(0).tolist())),
                 "positives_val": dict(zip(ACTIVE, yva[:, active_idx].sum(0).tolist()))},
        "thresholds_bayes": thr,
        "baselines_val": baselines,
        "main_model": model_metrics,
        "onnx": {"path": onnx_path.relative_to(ROOT).as_posix(), "size_mb": round(onnx_path.stat().st_size / 2**20, 2)},
        "runtime_s": round(time.time() - t0, 1),
    }
    result_path = write_result("train_mw40", payload, seed=best_run["seed"])
    meta = {
        "labels": labels, "temperature": T, "tau": tau, "score": "joint_energy",
        "backbone": "efficientnet_b0", "trained_on": "mw40_v01", "trained_labels": ACTIVE,
        "warning": WARNING, "metrics": model_metrics,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "commit": git_commit(),
    }
    (MODELS / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nBaseline (val):")
    for name, m in baselines.items():
        print(f"  {name:22s} mAP {m['mAP']:.4f} · macro-F1 {m['macro_f1']:.4f} · exact {m['exact_match']:.4f}")
    print(f"Mô hình chính: mAP val {maps.mean():.4f} ± {maps.std():.4f} (3 seed) · T = {T:.3f}")
    print(f"  sau T: macro-F1 {head_metrics['macro_f1']:.4f} · exact {head_metrics['exact_match']:.4f}")
    print(f"Lớp mở: τ = {tau:.3f} · AUROC {auroc:.4f} · OOD bị chấp nhận tại τ {fpr_at_tau:.3f}")
    print(f"ONNX: {onnx_path} ({payload['onnx']['size_mb']} MB, lệch tối đa {max_diff:.2e})")
    print(f"Kết quả: {result_path} · {payload['runtime_s']} s")
    print(f"\n{WARNING}")


if __name__ == "__main__":
    main()
