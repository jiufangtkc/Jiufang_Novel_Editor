@echo off
echo Cleaning up old build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Running PyInstaller...
.venv\Scripts\pyinstaller.exe ^
    --noconfirm ^
    --noconsole ^
    --name "Jiufang_Novel_Editor" ^
    --icon "resources/icons/app_icon.ico" ^
    --add-data "resources;resources" ^
    --exclude-module pytest ^
    main.py

echo Build finished! Check the dist\Jiufang_Novel_Editor folder.
pause
