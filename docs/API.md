# Hợp đồng API ViMedWaste (BE ↔ FE)

- BE: FastAPI, thư mục `ViMedWaste/backend/`, cổng **8000**, tiền tố **`/api`**. Dùng lại package `vimedwaste` (config, decision, inference).
- FE: Angular 20 (standalone), thư mục `ViMedWaste/frontend/`, cổng **4200**, proxy `/api` → `http://localhost:8000`.
- JSON, thời gian ISO 8601 có múi giờ, tiếng Việt trong các trường hiển thị.
- Trạng thái quyết định: `"CANH_BAO" | "PHU_HOP" | "KHONG_XAC_DINH"` (đúng hằng số trong `vimedwaste/decision.py`).
- Mọi sự kiện có cờ `simulated` (true khi sinh từ bộ Medical Waste 4.0 bằng `/api/simulate`). FE hiện huy hiệu "Dữ liệu mô phỏng" khi có.

## Kiểu dữ liệu

```ts
Bin        = { code: "B1".."B5", name: string, short: string, color: "#hex", border: "#hex" }
LabelInfo  = { code: "L01".."L10", name: string, group: string, group_name: string,
               correct_bins: string[], c_fn: number, threshold: number, example: string }
LabelScore = { code, name, prob: number, threshold: number, present: boolean,
               violation: boolean, correct_bins: string[] }
Decision   = { status, bin_type, title: string,            // ví dụ "Kim tiêm trong thùng xanh"
               labels: LabelScore[], violations: string[],  // mã nhãn, nguy hiểm trước
               ood_score: number|null, tau: number|null, accepted: boolean,
               model: { available: boolean, trained_on: string|null, warning: string|null } }
Zone       = { zone_no: number, bin_type: string, box: [x, y, w, h] }   // tỷ lệ 0..1 trên ảnh camera
Settings   = { still_seconds: number, motion_sensitivity: number /*0..1*/,
               buzzer_volume: number /*0..1*/, dry_run: boolean }
Station    = { id: string, name: string, location: string, online: boolean,
               last_seen: string|null, zones: Zone[], settings: Settings }
EventSummary = { id: number, time: string, station_id, station_name, zone_no, bin_type,
                 status, title, handling: "CHUA_XU_LY"|"DA_LAY_RA"|"CHO_XEM_LAI"|null,
                 feedback: "DUNG"|"NHAM"|null, simulated: boolean }
EventDetail  = EventSummary & { decision: Decision,
                 images: { before: string|null, after: string, gradcam: string|null },  // URL tương đối /api/...
                 change_box: [x, y, w, h] | null,    // vùng thay đổi giữa trước/sau, tỷ lệ 0..1
                 timeline: { time: string, text: string }[] }
```

## Endpoint

| Method | Đường dẫn | Mô tả |
|---|---|---|
| GET | `/api/health` | `{status:"ok", model_available}` |
| GET | `/api/labels` | `{labels: LabelInfo[], bins: Bin[], compatibility: {[label]: string[]}}` |
| GET | `/api/model` | meta.json + metrics tóm tắt + `available` |
| POST | `/api/predict` | multipart `image`, `bin_type` → `Decision` + `gradcam: string|null` (data URL PNG, nhãn vi phạm đầu tiên hoặc nhãn cao nhất) |
| GET | `/api/stations` | `Station[]` |
| GET | `/api/stations/{id}` | `Station` |
| PUT | `/api/stations/{id}/config` | body `{zones: Zone[], settings: Settings}` → `Station` |
| GET | `/api/stations/{id}/snapshot` | `image/jpeg` ảnh camera gần nhất (chưa có → ảnh nền xám có chữ) |
| POST | `/api/stations/{id}/heartbeat` | cập nhật `last_seen` (thiết bị gọi định kỳ) |
| POST | `/api/stations/{id}/capture` | multipart `zone_no`, `image`, `before_image?` → `EventDetail`. Đây là API thiết bị Pi gọi sau khi tay rút ra. Có `dry_run` thì vẫn ghi sự kiện. |
| POST | `/api/stations/{id}/test-capture` | multipart `zone_no`, `image?` (thiếu → dùng snapshot) → `Decision` (không ghi sự kiện) |
| GET | `/api/events?status=&station_id=&limit=50` | `EventSummary[]`, mới nhất trước |
| GET | `/api/events/{id}` | `EventDetail` |
| GET | `/api/events/{id}/image/{kind}` | `kind = before|after|gradcam` → `image/jpeg|png` |
| POST | `/api/events/{id}/feedback` | `{verdict:"DUNG"|"NHAM", note?}` → `EventDetail`. NHAM → đưa ảnh vào hàng chờ gán nhãn lại (bảng `relabel_queue`) |
| POST | `/api/events/{id}/handling` | `{handling}` → `EventDetail` |
| GET | `/api/stats/overview?date=YYYY-MM-DD` | `{date, total, warnings, handled_pct, unknown, top_mislabels:[{code,name,count}], stations:[{id,name,online}], simulated:boolean}` (mặc định hôm nay) |
| POST | `/api/simulate` | `{n: number (mặc định 12)}` → sinh n sự kiện từ ảnh Medical Waste 4.0 (gồm cả ảnh OOD), gán ngẫu nhiên trạm/vùng, `simulated=true` |

## Dữ liệu khởi tạo

3 trạm mẫu, mỗi trạm 4 vùng (B1, B2, B4, B5):
`tram-01` "Xe tiêm 01", `tram-02` "Buồng thủ thuật", `tram-03` "Xe tiêm 02" (location "[Tên khoa]").
Trạm `online` khi `last_seen` trong 2 phút gần nhất.
