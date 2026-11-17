"""Nghiệp vụ backend, mỗi module một mảng:

- stations   : trạm, cấu hình vùng thùng, snapshot, chụp thử
- events     : xử lý ảnh chụp → sự kiện, phản hồi, trạng thái xử lý
- stats      : số liệu tổng quan
- simulation : sinh sự kiện mô phỏng từ dữ liệu ngoài
- model_service, catalog, imaging : mô hình, danh mục nhãn/thùng, xử lý ảnh
"""


class NotFound(LookupError):
    """Không tìm thấy trạm, vùng hoặc sự kiện → HTTP 404."""
