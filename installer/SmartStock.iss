; SmartStock — Inno Setup 6
; Compile from repo:  powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
; Or:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\SmartStock.iss" /DINSTALL_CODE="YourSecret"

#define MyAppName "SmartStock"
#define MyAppVersion "1.0.0"
#ifndef INSTALL_CODE
#define INSTALL_CODE "AlhamdulilA"
#endif

#define MyAppPublisher "SmartStock"
#define MyAppExeName "SmartStock.exe"

[Setup]
AppId={{2F4A8B1C-3D5E-6F70-8192-A3B4C5D6E7F8}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Per-user install (no admin) — %LocalAppData%\Programs\SmartStock
DefaultDirName={localappdata}\Programs\{#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=SmartStock_Setup
SetupIconFile=..\assets\smartstock.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
LicenseFile=
InfoBeforeFile=
InfoAfterFile=
VersionInfoVersion=1.0.0.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppName} Setup
VersionInfoProductName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start {#MyAppName} when Windows logs on"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; PyInstaller one-folder output (entire tree)
Source: "..\dist\V01\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "write_install_verified.ps1"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Run]
Filename: "{sys}\WindowsPowerShell\v1.0\powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{tmp}\write_install_verified.ps1"""; StatusMsg: "Recording installation..."; Flags: runhidden waituntilterminated; AfterInstall: VerifyInstallVerified
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  InstallCodePage: TWizardPage;
  InstallCodeEdit: TNewEdit;

procedure VerifyInstallVerified;
var
  MarkerPath: String;
begin
  MarkerPath := ExpandConstant('{localappdata}\SmartStock\.install_verified');
  if not FileExists(MarkerPath) then
  begin
    Log('Install verification marker missing: ' + MarkerPath);
    MsgBox('Installation verification could not be recorded. Setup cannot continue.', mbError, MB_OK);
    Abort;
  end;
  Log('Install verification marker created: ' + MarkerPath);
end;

procedure InitializeWizard;
begin
  InstallCodePage := CreateCustomPage(wpWelcome,
    'Installation code',
    'Enter the installation code supplied with your software. It must match the value configured for this build.');
  InstallCodeEdit := TNewEdit.Create(InstallCodePage);
  InstallCodeEdit.Parent := InstallCodePage.Surface;
  InstallCodeEdit.Left := ScaleX(0);
  InstallCodeEdit.Top := ScaleY(0);
  InstallCodeEdit.Width := InstallCodePage.SurfaceWidth;
  InstallCodeEdit.Height := ScaleY(23);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = InstallCodePage.ID then
  begin
    if InstallCodeEdit.Text <> ExpandConstant('{#INSTALL_CODE}') then
    begin
      MsgBox('Invalid installation code. Check with your vendor and try again.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
