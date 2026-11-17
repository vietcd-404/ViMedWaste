"""Đẩy ViMedWaste lên Hugging Face Spaces (Docker Space, cổng 7860).

Chuẩn bị một lần:
  1. Tạo tài khoản https://huggingface.co và token quyền "Write" (Settings → Access Tokens).
  2. hf auth login            (dán token khi được hỏi; token không lưu trong dự án)

Mỗi lần deploy (từ thư mục ViMedWaste):
  python scripts/build_demo_data.py                     # nếu chưa có data/demo/
  python scripts/deploy_hf_space.py --repo <tên-tài-khoản>/vimedwaste

Script gom đúng những file Dockerfile cần vào build/hf_space/, thêm README có cấu hình Space,
tạo Space nếu chưa có, đặt mật khẩu (secret VIMEDWASTE_PASSWORD) rồi tải lên. Hugging Face tự build.
"""
from __future__ import annotations

import argparse
import getpass
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "build" / "hf_space"

INCLUDE = ["Dockerfile", ".dockerignore", "pyproject.toml", "src", "backend", "configs",
           "artifacts/models", "data/demo", "frontend"]
SKIP = shutil.ignore_patterns("__pycache__", "*.egg-info", "node_modules", "dist", ".angular",
                              "data", "*.db", ".vscode")   # "data" chỉ bỏ backend/data (DB dev)

SPACE_README = """---
title: ViMedWaste
emoji: 🩺
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
short_description: Cảnh báo bỏ sai chất thải y tế tại nguồn (TT 20/2021)
---

# ViMedWaste – bản demo

Giao diện quản lý trạm thùng thông minh: tổng quan, sự kiện (ảnh trước/sau, Grad-CAM), cấu hình vùng thùng,
kiểm tra ảnh, bảng nhãn theo Thông tư 20/2021.

- Truy cập cần mật khẩu (hỏi nhóm nghiên cứu).
- **Dữ liệu là mô phỏng** từ bộ Medical Waste 4.0 (Bruno và cs., 2023, CC BY 4.0), tự sinh lại mỗi lần Space khởi động.
- Mô hình hiện chỉ huấn luyện trên 3/10 nhãn của dữ liệu ngoài, chỉ để chạy thử hệ thống, không phải kết quả nghiên cứu.
"""


def stage() -> Path:
    if not (ROOT / "data" / "demo" / "metadata.csv").exists():
        raise SystemExit("Chưa có data/demo/. Chạy: python scripts/build_demo_data.py")
    if not (ROOT / "artifacts" / "models" / "vimedwaste.onnx").exists():
        raise SystemExit("Chưa có artifacts/models/vimedwaste.onnx. Chạy: .\\scripts\\dev.ps1 train")
    shutil.rmtree(STAGE, ignore_errors=True)
    STAGE.mkdir(parents=True)
    for rel in INCLUDE:
        src, dst = ROOT / rel, STAGE / rel
        if src.is_dir():
            # data/demo phải giữ nguyên, chỉ lọc "data" bên trong backend/
            shutil.copytree(src, dst, ignore=None if rel.startswith("data") else SKIP)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    (STAGE / "README.md").write_text(SPACE_README, encoding="utf-8")
    size = sum(f.stat().st_size for f in STAGE.rglob("*") if f.is_file()) / 2**20
    print(f"Đã gom {sum(1 for f in STAGE.rglob('*') if f.is_file())} file ({size:.1f} MB) → {STAGE}")
    return STAGE


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="<tài-khoản>/<tên-space>, ví dụ nhom-vimedwaste/vimedwaste")
    ap.add_argument("--private", action="store_true", help="Space riêng tư (người khác không xem được)")
    ap.add_argument("--password", help="mật khẩu truy cập; bỏ trống thì được hỏi")
    ap.add_argument("--stage-only", action="store_true", help="chỉ gom file, không tải lên")
    args = ap.parse_args()

    folder = stage()
    if args.stage_only:
        return

    from huggingface_hub import HfApi

    api = HfApi()
    user = api.whoami()["name"]
    print(f"Đăng nhập Hugging Face: {user}")
    api.create_repo(args.repo, repo_type="space", space_sdk="docker", private=args.private, exist_ok=True)

    password = args.password or getpass.getpass("Mật khẩu truy cập demo (Enter = không khóa): ")
    if password:
        api.add_space_secret(args.repo, "VIMEDWASTE_PASSWORD", password)
        print("Đã đặt secret VIMEDWASTE_PASSWORD")
    else:
        print("CẢNH BÁO: không đặt mật khẩu, ai có link cũng sửa được cấu hình trạm.")

    api.upload_folder(repo_id=args.repo, repo_type="space", folder_path=str(folder),
                      commit_message="Deploy ViMedWaste", delete_patterns=["*"])
    print(f"Đã tải lên. Hugging Face đang build (khoảng 5–10 phút):")
    print(f"  https://huggingface.co/spaces/{args.repo}")


if __name__ == "__main__":
    main()
