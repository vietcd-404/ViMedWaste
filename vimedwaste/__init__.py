"""ViMedWaste – khung dữ liệu cảnh báo bỏ sai chất thải y tế theo TT 20/2021."""

import sys

__version__ = "0.1.0"

# Terminal Windows mặc định cp1252 không in được tiếng Việt.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure") and (_stream.encoding or "").lower() != "utf-8":
        _stream.reconfigure(encoding="utf-8", errors="replace")
