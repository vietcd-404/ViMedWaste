# ViMedWaste

Phát hiện chất thải y tế bỏ sai thùng **tại nguồn** theo Thông tư 20/2021: ảnh miệng thùng + loại thùng → **CẢNH BÁO / PHÙ HỢP / KHÔNG XÁC ĐỊNH**.
Phân loại đa nhãn 10 nhãn (L01–L10), 5 loại thùng (B1–B5), nhận dạng lớp mở, chạy ONNX trên CPU.

> Mô hình hiện tại chỉ huấn luyện trên dữ liệu ngoài Medical Waste 4.0 (3/10 nhãn) để chạy thử toàn bộ hệ thống. Không dùng làm bằng chứng cho giả thuyết.

## Kiến trúc

```
                ┌────────── src/vimedwaste  (thư viện ML) ──────────┐
 ảnh tự chụp ─► │ data/      bước 2: ẩn danh, gán nhãn, κ, lọc trùng, │
 dữ liệu ngoài  │            chia tập, kiểm tra                       │
                │ training/  bước 3–5: train, hiệu chuẩn, xuất ONNX ──┼─► artifacts/models/
                │ serving/   suy luận ONNX + quy tắc cảnh báo         │      vimedwaste.onnx
                │ core/      đường dẫn, cấu hình nhãn, lược đồ        │      meta.json
                └───────────────────────────┬─────────────────────────┘
                                            │ import
 Raspberry Pi ──POST /capture──►  backend/ (FastAPI :8000) ◄──/api──  frontend/ (Angular :4200)
                                  SQLite + ảnh sự kiện                 quản lý trạm, sự kiện
```

Chi tiết: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · API: [docs/API.md](docs/API.md) · Dữ liệu: [docs/DATA_PIPELINE.md](docs/DATA_PIPELINE.md)

## Cấu trúc thư mục

```
ViMedWaste/
├─ configs/labels.yaml     10 nhãn, 5 thùng, ma trận tương thích, chi phí sai, ngưỡng κ
├─ src/vimedwaste/         thư viện ML (pip install -e .)
│  ├─ core/                paths · config · schema · utils
│  ├─ data/                bước 2 – tiền xử lý dữ liệu
│  ├─ training/            bước 3–5 – train_mw40.py
│  └─ serving/             inference.py (ONNX) · decision.py (cảnh báo)
├─ backend/                FastAPI: main · schemas · routers/ · services/
├─ frontend/               Angular 20
├─ demo/                   giao diện Streamlit cũ (demo nhanh)
├─ artifacts/              do code sinh ra: models/ (ONNX, meta.json) · results/ (*.json)
├─ data/                   external/ (bảng dữ liệu ngoài) · tables/ · raw/ (không lên Git)
├─ docs/                   ARCHITECTURE · API · DATA_PIPELINE
├─ scripts/dev.ps1         lệnh chạy nhanh
└─ tests/                  core · data · training · serving · backend · demo
```

## Chạy nhanh

Yêu cầu: Python 3.11 (môi trường ảo `..\.venv`), Node 20+.

```powershell
.\scripts\dev.ps1 setup       # lần đầu: cài Python package + npm install
.\scripts\dev.ps1 test        # toàn bộ test

.\scripts\dev.ps1 backend     # terminal 1 → http://localhost:8000/docs
.\scripts\dev.ps1 frontend    # terminal 2 → http://localhost:4200
.\scripts\dev.ps1 simulate    # sinh sự kiện mô phỏng cho trang Tổng quan

.\scripts\dev.ps1 train       # train lại mô hình → artifacts/models/
```

PowerShell chặn script thì chạy một lần: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Deploy lên Hugging Face Spaces

Một container Docker (`Dockerfile`): build Angular, FastAPI phục vụ cả API lẫn giao diện ở cổng 7860, khóa bằng mật khẩu,
tự sinh 24 sự kiện mô phỏng từ bộ ảnh demo nhỏ (`data/demo/`, 168 ảnh) mỗi lần khởi động.

```powershell
.\scripts\dev.ps1 docker                          # thử trên máy: http://localhost:7860 (mật khẩu: demo)
..\.venv\Scripts\hf.exe auth login                # một lần, dán token quyền Write
.\scripts\dev.ps1 deploy <tài-khoản>/vimedwaste   # gom file → tạo Space → đặt mật khẩu → tải lên
```

Gói miễn phí không giữ dữ liệu khi Space khởi động lại. Không đưa ảnh thật của bệnh viện lên đây.

## Quy trình phát triển

Theo 6 bước (bám bài giảng Thân Quang Khoát, `../11_HE_THONG_PROMPT_THUC_CHIEN.md`):

| Bước | Ở đâu trong code | Trạng thái |
|---|---|---|
| 1. Xác định bài toán T-P-E | `configs/labels.yaml` | Xong |
| 2. Tiền xử lý dữ liệu | `src/vimedwaste/data/` | Khung + code xong, chờ ảnh tự chụp |
| 3. Mô hình & baseline | `src/vimedwaste/training/` | Chạy thử trên dữ liệu ngoài |
| 4. Hàm mất mát & regularization | `src/vimedwaste/training/` | Chạy thử |
| 5. Đánh giá & tránh rò rỉ | `data/split.py`, `data/dedup.py`, `training/` | Chạy thử |
| 6. Phân tích & vòng lặp | `backend` phản hồi "Báo nhầm" → hàng chờ gán nhãn lại | Có khung |
