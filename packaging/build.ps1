# Build dist\PixelBuddy\PixelBuddy.exe (PyInstaller, onedir) and, if Inno Setup is installed, dist\PixelBuddy-Setup.exe
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$py = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }

& $py -m pip install -q -r requirements-dev.txt
& $py packaging\make_icon.py

& $py -m PyInstaller --noconfirm --clean --windowed --onedir --name PixelBuddy `
    --icon "$root\packaging\buddy.ico" --paths "$root" --distpath dist --workpath build --specpath build `
    --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets `
    --exclude-module PySide6.QtPdf --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick `
    "$root/buddy.pyw"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
Write-Host "OK: dist\PixelBuddy\PixelBuddy.exe"

$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
              "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if ($iscc) {
    & $iscc packaging\PixelBuddy.iss
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
    Write-Host "OK: dist\PixelBuddy-Setup.exe"
} else {
    Write-Host "ไม่พบ Inno Setup (ISCC.exe) - ข้ามขั้นตอนสร้างตัวติดตั้ง (ติดตั้งได้จาก https://jrsoftware.org/isinfo.php แล้วรันสคริปต์นี้ใหม่)"
}
