[Setup]
AppName=Jiufang Novel Editor
AppVersion=1.0
DefaultDirName={localappdata}\Jiufang_Novel_Editor
DefaultGroupName=Jiufang Novel Editor
UninstallDisplayIcon={app}\Jiufang_Novel_Editor.exe
Compression=lzma2
SolidCompression=yes
OutputDir=userdocs:Inno Setup Examples Output
OutputBaseFilename=Jiufang_Setup
; 如果需要未來無感更新，不要勾選需要管理員權限
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
; 在安裝新版本前，刪除舊版的程式核心資料夾，避免舊套件殘留。
; 注意：不能直接刪除 {app}，因為裡面放著使用者的存檔 (Temp_doc / story)！
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\Jiufang_Novel_Editor\Jiufang_Novel_Editor.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Jiufang_Novel_Editor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 忽略開發相關檔案已在 PyInstaller 階段過濾

[Icons]
Name: "{group}\Jiufang Novel Editor"; Filename: "{app}\Jiufang_Novel_Editor.exe"
Name: "{userdesktop}\Jiufang Novel Editor"; Filename: "{app}\Jiufang_Novel_Editor.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Jiufang_Novel_Editor.exe"; Description: "{cm:LaunchProgram,Jiufang Novel Editor}"; Flags: nowait postinstall skipifsilent
