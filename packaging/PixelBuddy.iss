; Inno Setup script. Build with packaging\build.ps1 (after PyInstaller has produced dist\PixelBuddy\).
; Per-user install: no admin prompt.
#define AppName "Pixel Buddy"
#define AppExe "PixelBuddy.exe"
#ifndef AppVersion
  #define AppVersion "0.4.1"
#endif

[Setup]
AppId={{6F1D3C52-7B0E-4E55-9C7A-5B1D0C6A9E21}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Pixel Buddy
DefaultDirName={localappdata}\Programs\PixelBuddy
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=PixelBuddy-Setup
SetupIconFile=buddy.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "autostart"; Description: "Run Pixel Buddy automatically at Windows startup"
Name: "hooks"; Description: "Install hooks in Claude Code (~/.claude/settings.json, original is backed up)"

[Files]
Source: "..\dist\PixelBuddy\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "PixelBuddy"; \
    ValueData: """{app}\{#AppExe}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#AppExe}"; Parameters: "--install-hooks"; Flags: runhidden; Tasks: hooks
Filename: "{app}\{#AppExe}"; Description: "Launch Pixel Buddy now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/im {#AppExe} /f"; Flags: runhidden; RunOnceId: "KillBuddy"
Filename: "{app}\{#AppExe}"; Parameters: "--cleanup"; Flags: runhidden; RunOnceId: "CleanupBuddy"
