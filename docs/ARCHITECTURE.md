# Kiến trúc ViMedWaste

## 1. Ba khối và cách phụ thuộc

```
frontend (Angular)  ──HTTP /api──►  backend (FastAPI)  ──import──►  vimedwaste (thư viện ML)
                                         │                               │
                                         ▼                               ▼
                                 SQLite + ảnh sự kiện           artifacts/models/*.onnx
                                 (backend/data/)                configs/labels.yaml
```

- `vimedwaste` **không biết** gì về backend hay frontend. Train, chạy test và dùng trên Pi đều độc lập.
- `backend` chỉ ghép thư viện với HTTP + lưu trữ. Nghiệp vụ ở `services/`, route mỏng ở `routers/`.
- `frontend` chỉ nói chuyện với backend qua hợp đồng `docs/API.md`.

## 2. Thư viện `src/vimedwaste`

| Gói | File | Vai trò |
|---|---|---|
| `core` | `paths.py` | Mọi đường dẫn ở một chỗ |
| | `config.py` | Đọc `configs/labels.yaml` → nhãn, thùng, ma trận A, chi phí sai |
| | `schema.py` | Tên cột 4 bảng CSV |
| | `utils.py` | Ghi `artifacts/results/*.json` kèm commit + seed |
| `data` (bước 2) | `anonymize` → `cvat_export` → `agreement` → `dedup` → `split` → `validate_metadata` | Luồng 6 bước từ ảnh chụp đến Dataset v1.0 |
| | `import_mw40` | Nhập dữ liệu ngoài Medical Waste 4.0 |
| `training` (bước 3–5) | `train_mw40.py` | Đặc trưng EfficientNet-B0 → baseline + đầu tuyến tính → hiệu chuẩn T, τ → ONNX |
| `serving` | `inference.py` | Tiền xử lý + chạy ONNX → 10 xác suất + điểm lớp mở |
| | `decision.py` | Ngưỡng Bayes + ma trận A → CẢNH BÁO / PHÙ HỢP / KHÔNG XÁC ĐỊNH |

## 3. Luồng huấn luyện

```
ảnh + nhãn (data/external/mw40_v01)
  → preprocess (224×224, chuẩn hóa ImageNet)
  → EfficientNet-B0 đóng băng → vector 1280 số       (cache: data/features/)
  → baseline: Logistic / SVM / KNN / RF               (so sánh – No Free Lunch)
  → đầu tuyến tính 1280→10, BCE, AdamW, dừng sớm, 3 seed
  → temperature scaling T, ngưỡng lớp mở τ (giữ 95 % val)
  → artifacts/models/vimedwaste.onnx + meta.json + head.pt
  → artifacts/results/train_mw40.json
```

## 4. Luồng suy luận (mỗi lần bỏ rác)

```
ảnh vùng thùng + loại thùng b
  → vimedwaste.onnx → 10 xác suất p_k, điểm S(x)
  → S(x) < τ ?              có → KHÔNG XÁC ĐỊNH
  → nhãn có mặt: p_k ≥ t_k  (t_k = 1 / (1 + C_FN,k): kim tiêm 0,09 · lây nhiễm 0,17 · thường 0,5)
  → nhãn k không được bỏ vào b ?  có → CẢNH BÁO (kèm thùng đúng), không → PHÙ HỢP
  → backend ghi sự kiện, Grad-CAM, vùng thay đổi; frontend hiển thị; người quản lý xác nhận / báo nhầm
```

## 5. Backend

```
backend/
├─ main.py       tạo app, gắn router, lỗi 404/503
├─ schemas.py    kiểu dữ liệu đầu vào (pydantic)
├─ settings.py   đường dẫn DB, CORS, cửa sổ online
├─ db.py         SQLite: stations, events, relabel_queue
├─ routers/      system · stations · events · stats
└─ services/     stations · events · stats · simulation · model_service · catalog · imaging
```

Khi chạy dự đoán, backend chỉ cần: `artifacts/models/vimedwaste.onnx`, `meta.json`, `configs/labels.yaml`.
`head.pt` + PyTorch chỉ để vẽ Grad-CAM; `data/external/` chỉ để sinh dữ liệu mô phỏng.

## 6. Thay mô hình

Train lại (`.\scripts\dev.ps1 train`) ghi đè `artifacts/models/`, khởi động lại backend. Không sửa code.
