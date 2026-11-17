<#
.SYNOPSIS
  Lệnh chạy nhanh cho ViMedWaste. Chạy từ thư mục ViMedWaste:
    .\scripts\dev.ps1 <lệnh>

  setup      cài package Python (mọi nhóm) + npm install cho frontend
  test       chạy toàn bộ test Python
  backend    chạy FastAPI ở http://localhost:8000 (Swagger: /docs)
  frontend   chạy Angular ở http://localhost:4200 (cần backend)
  demo       chạy giao diện Streamlit cũ ở http://localhost:8501
  train      train lại mô hình trên Medical Waste 4.0 → artifacts/models/
  import     nhập lại dữ liệu Medical Waste 4.0 → data/external/mw40_v01/
  simulate   sinh 12 sự kiện mô phỏng (backend phải đang chạy)
  docker     build + chạy container giống Hugging Face ở http://localhost:7860
  deploy     đẩy lên Hugging Face Spaces:  .\scripts\dev.ps1 deploy <tài-khoản>/vimedwaste
#>
param([Parameter(Position = 0)][string]$Command = "help", [Parameter(Position = 1)][string]$Arg = "")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path (Split-Path -Parent $Root) ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) { $Py = "python" }
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Set-Location $Root

switch ($Command) {
    "setup"    { & $Py -m pip install -e ".[all]"; Push-Location frontend; npm install; Pop-Location }
    "test"     { & $Py -m pytest -q }
    "backend"  { & $Py -m uvicorn backend.main:app --port 8000 --reload --reload-dir backend --reload-dir src }
    "frontend" { Push-Location frontend; npm start; Pop-Location }
    "demo"     { & $Py -m streamlit run demo\streamlit_app.py }
    "train"    { & $Py -m vimedwaste.training.train_mw40 }
    "import"   { & $Py -m vimedwaste.data.import_mw40 --src "..\Medical Waste 4.0" }
    "simulate" { Invoke-RestMethod -Method Post http://localhost:8000/api/simulate -ContentType "application/json" -Body '{"n": 12}' }
    "docker"   {
        if (-not (Test-Path data\demo\metadata.csv)) { & $Py scripts\build_demo_data.py }
        docker build -t vimedwaste:local .
        docker run --rm -p 7860:7860 -e VIMEDWASTE_PASSWORD=demo vimedwaste:local   # mật khẩu thử: demo
    }
    "deploy"   {
        if (-not $Arg) { throw "Thiếu tên Space, ví dụ: .\scripts\dev.ps1 deploy ten-tai-khoan/vimedwaste" }
        if (-not (Test-Path data\demo\metadata.csv)) { & $Py scripts\build_demo_data.py }
        & $Py scripts\deploy_hf_space.py --repo $Arg
    }
    default    { Get-Help $PSCommandPath -Detailed | Out-String | Write-Host }
}
