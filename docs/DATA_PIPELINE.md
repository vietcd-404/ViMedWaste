# Luồng dữ liệu (bước 2)

Đặc tả gốc: `../06_DAC_TA_TRIEN_KHAI.md` mục 2–3. Chạy từ thư mục `ViMedWaste`, môi trường ảo đã bật.

## Một lô ảnh tự chụp

```powershell
# 1–2. Ẩn danh (sau khi đã làm mờ thông tin bệnh nhân và loại ảnh có người)
python -m vimedwaste.data.anonymize --src data\raw\2026-11-20_S01 --site S01 --date 2026-11-20 --bin B2
python -m vimedwaste.data.dedup --metadata data\tables\metadata.csv

# 3. Gán nhãn trên CVAT (tag L01…L10, bad_quality), mỗi người một task, rồi xuất XML
python -m vimedwaste.data.cvat_export --xml exports\lo01_dat.xml --annotator dat --batch lo01
python -m vimedwaste.data.cvat_export --xml exports\lo01_lam.xml --annotator lam --batch lo01

# 4. Đồng thuận và phân xử
python -m vimedwaste.data.agreement kappa --batch lo01
python -m vimedwaste.data.agreement resolve            # → labels.csv, disagreements.csv
python -m vimedwaste.data.agreement resolve --adjudication data\tables\adjudication.csv

# 5–6. Chia tập (một lần, sau đó khóa), kiểm tra rò rỉ và ràng buộc
python -m vimedwaste.data.split
python -m vimedwaste.data.dedup --metadata data\tables\metadata.csv --splits data\tables\splits.csv
python -m vimedwaste.data.validate_metadata --check-files
```

| Bước | Script | Người phụ trách |
|---|---|---|
| Ẩn danh | `anonymize.py` | Đạt |
| CVAT → bảng | `cvat_export.py` | Việt |
| κ, phân xử | `agreement.py` | Lâm |
| Lọc trùng | `dedup.py` | Lâm |
| Chia tập | `split.py` | Lâm |
| Kiểm tra ràng buộc | `validate_metadata.py` | Em |

## Dữ liệu ngoài: Medical Waste 4.0

```powershell
python -m vimedwaste.data.import_mw40 --src "..\Medical Waste 4.0"
python -m vimedwaste.data.validate_metadata --tables data\external\mw40_v01 --check-files
python -m vimedwaste.data.dedup --metadata data\external\mw40_v01\metadata.csv --splits data\external\mw40_v01\splits.csv --tag mw40
```

Quy tắc: chỉ dùng chạy thử và pretrain; không vào test; không tính vào 2.500 ảnh.
Mỗi lớp được chụp trong một phiên ngắn với cùng vài vật, nên chia theo khối thời gian, không chia ngẫu nhiên.

## Việc làm tay

- Làm mờ tên người bệnh, mã hồ sơ, tên khoa trên bao bì; loại ảnh có người (`--exclude`).
- Xem lại vài cặp trong `near_duplicates.csv` để chỉnh ngưỡng `phash_max_distance`.
- Người thứ ba phân xử các ảnh trong `disagreements.csv`, ghi vào `adjudication.csv` cùng cột với annotations.
