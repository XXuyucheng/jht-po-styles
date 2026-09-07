; Inno Setup script — compile on Windows after packaging\build_windows.ps1
; Requires: https://jrsoftware.org/isinfo.php
; Output: dist\JhtPoStyles-Setup.exe

#define MyAppName "聚水潭采购单款号提取"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "jht-po-styles"
#define MyAppExeName "JhtPoStyles.exe"

[Setup]
AppId={{A7C3E91B-4D2F-4B8A-9E11-7C2B1F0A9D83}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\JhtPoStyles
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=JhtPoStyles-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
; ChineseSimplified.isl may be missing on some Inno Setup installs — English is enough
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "..\dist\JhtPoStyles\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  MsgBox('安装完成后首次提取款号时，会自动下载 Chromium 浏览器组件（需联网，约 150MB），请耐心等待。', mbInformation, MB_OK);
end;
