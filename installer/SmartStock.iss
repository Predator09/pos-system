; SmartStock Windows installer (Inno Setup 6+).
;
; 1. Build the app folder first:  python -m PyInstaller smartstock.spec  (from parent directory)
; 2. Set your install code below (or compile with: iscc /DINSTALL_CODE=YourSecret installer\SmartStock.iss)
; 3. Open this file in Inno Setup and Build, or run ISCC.exe on this file.

#ifndef INSTALL_CODE
#define INSTALL_CODE "AlhamdulilA"
#endif

#define MyAppName "SmartStock"
#define MyAppPublisher "Your company name"
#define MyAppExeName "SmartStock.exe"
; PyInstaller output (build from repo root: python -m PyInstaller smartstock.spec)
#define BuildOutputDir "..\\dist\\V01"

[Setup]
AppId={{B5F8D2A1-4C3E-4F1B-9D0A-1E2F3A4B5C6D}
AppName={#MyAppName}
AppVersion=1.0.0
AppPublisher={#MyAppPublisher}
; Per-user folder (no admin UAC) so optional "start with Windows" writes HKCU Run for the actual shop user, not an elevated admin profile.
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\dist_installer
OutputBaseFilename=SmartStock_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Wizard + shortcuts: same artwork as the built EXE (see assets/smartstock.ico + PyInstaller spec).
SetupIconFile=..\assets\smartstock.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Start {#MyAppName} when Windows logs on (current user)"; GroupDescription: "Options:"; Flags: unchecked

[Files]
Source: "{#BuildOutputDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  CodePage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  CodePage := CreateInputQueryPage(wpWelcome,
    'Authorization',
    'Installation code required',
    'Enter the installation code you received. Installation cannot continue without the correct code.');
  CodePage.Add('Installation code:', True);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = CodePage.ID then
  begin
    if CodePage.Values[0] <> '{#INSTALL_CODE}' then
    begin
      MsgBox('That code is not valid. Check with your vendor and try again.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
  Marker: String;
begin
  { After a successful install, mark this PC so the app does not ask for the code again. }
  if CurStep = ssPostInstall then
  begin
    DataDir := ExpandConstant('{localappdata}\SmartStock');
    if not DirExists(DataDir) then
      CreateDir(DataDir);
    Marker := DataDir + '\.install_verified';
    SaveStringToFile(Marker, '1', False);
  end;
end;
