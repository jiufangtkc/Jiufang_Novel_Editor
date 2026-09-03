@echo off
chcp 65001 >nul
setlocal
pushd "%~dp0..\.."

echo ============================================================
echo [九方小說編輯器] 開始打包程序 (專案路徑: %cd%)
echo ============================================================

echo 清理舊的建置檔案...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo 正在執行 PyInstaller 打包...
if exist .venv\Scripts\python.exe (
    .venv\Scripts\python.exe -m PyInstaller --noconfirm --noconsole --name "Jiufang_Novel_Editor" --icon "resources/icons/app_icon.ico" --add-data "resources;resources" --exclude-module pytest main.py
) else (
    python -m PyInstaller --noconfirm --noconsole --name "Jiufang_Novel_Editor" --icon "resources/icons/app_icon.ico" --add-data "resources;resources" --exclude-module pytest main.py
)

if exist Jiufang_Novel_Editor.spec del /f /q Jiufang_Novel_Editor.spec
if %ERRORLEVEL% equ 0 (
    echo ============================================================
    echo 打包完成！輸出資料夾: dist\Jiufang_Novel_Editor
    echo ============================================================
) else (
    echo ============================================================
    echo 打包過程發生錯誤，請檢查上方訊息。
    echo ============================================================
)

popd
pause
