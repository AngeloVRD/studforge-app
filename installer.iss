; Studforge Setup — Inno Setup 6 Script

#define AppName      "Studforge"
#define AppVersion   "1.0"
#define AppPublisher "Studforge"
#define AppURL       "https://github.com/AngeloVRD/studforge-app"

[Setup]
AppId={{8F2A1B3C-4D5E-6F70-A8B9-C0D1E2F34567}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Install to user folder — no admin needed (like Chrome, VS Code)
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest

AllowNoIcons=yes
OutputDir=.
OutputBaseFilename=Studforge-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\Studforge.exe

Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
WizardResizable=no
DisableWelcomePage=no

[Languages]
Name: "german";  MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
german.InstallingDeps=Flask & PyWebView werden installiert ...
english.InstallingDeps=Installing Flask & PyWebView ...
german.GeneratingIcon=Icon wird erstellt ...
english.GeneratingIcon=Generating icon ...

[Tasks]
Name: desktopicon; Description: "Verknüpfung auf dem Desktop erstellen"; \
  GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
; App launcher (tiny exe, no console window)
Source: "dist\Studforge.exe"; DestDir: "{app}"; Flags: ignoreversion

; Python scripts
Source: "app.py";    DestDir: "{app}"; Flags: ignoreversion
Source: "main.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "icon.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico";  DestDir: "{app}"; Flags: ignoreversion

; HTML templates
Source: "templates\*"; DestDir: "{app}\templates"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

; CSS / JS / assets
Source: "static\*"; DestDir: "{app}\static"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}";                     Filename: "{app}\Studforge.exe"; \
  Comment: "Studforge 3D Manufaktur"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut (optional)
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\Studforge.exe"; \
  Comment: "Studforge 3D Manufaktur"; Tasks: desktopicon

[Run]
; Offer to launch after install
Filename: "{app}\Studforge.exe"; \
  Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent

; ── Pascal Script ────────────────────────────────────────────────────────────
[Code]
var
  PythonPath: String;

{ Find python.exe in common locations }
function FindPython(): String;
var
  LA: String;
  i:  Integer;
  Paths: TArrayOfString;
begin
  LA := GetEnv('LOCALAPPDATA');
  SetArrayLength(Paths, 9);
  Paths[0] := LA + '\Programs\Python\Python311\python.exe';
  Paths[1] := LA + '\Programs\Python\Python312\python.exe';
  Paths[2] := LA + '\Programs\Python\Python313\python.exe';
  Paths[3] := LA + '\Programs\Python\Python310\python.exe';
  Paths[4] := LA + '\Programs\Python\Python39\python.exe';
  Paths[5] := 'C:\Python311\python.exe';
  Paths[6] := 'C:\Python312\python.exe';
  Paths[7] := 'C:\Python310\python.exe';
  Paths[8] := 'C:\Python39\python.exe';
  for i := 0 to 8 do
    if FileExists(Paths[i]) then begin
      Result := Paths[i];
      Exit;
    end;
  Result := '';
end;

{ Download and silently install Python 3.11 }
function InstallPython(): Boolean;
var
  Tmp:  String;
  Code: Integer;
begin
  Result := False;
  Tmp    := ExpandConstant('{tmp}\python-3.11.9-amd64.exe');

  WizardForm.StatusLabel.Caption := 'Python 3.11 wird heruntergeladen ...';

  if not Exec('powershell.exe',
    '-NoProfile -ExecutionPolicy Bypass -Command ' +
    '"Invoke-WebRequest -Uri ' +
    '''https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe''' +
    ' -OutFile ''' + Tmp + ''' -UseBasicParsing"',
    '', SW_HIDE, ewWaitUntilTerminated, Code) then Exit;

  if not FileExists(Tmp) then Exit;

  WizardForm.StatusLabel.Caption := 'Python 3.11 wird installiert ...';

  Exec(Tmp, '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1',
    '', SW_HIDE, ewWaitUntilTerminated, Code);

  DeleteFile(Tmp);
  Result := (Code = 0);
end;

{ Called before the wizard appears }
function InitializeSetup(): Boolean;
var
  Answer: Integer;
begin
  PythonPath := FindPython();
  if PythonPath <> '' then begin
    Result := True;
    Exit;
  end;

  Answer := MsgBox(
    'Python 3.11 ist nicht installiert.' + #13#10 + #13#10 +
    'Soll Python jetzt automatisch heruntergeladen werden?' + #13#10 +
    '(ca. 25 MB, Internetverbindung erforderlich)',
    mbConfirmation, MB_YESNO);

  if Answer = IDYES then begin
    if InstallPython() then begin
      PythonPath := FindPython();
      if PythonPath <> '' then begin
        Result := True;
        Exit;
      end;
    end;
    MsgBox('Python Installation fehlgeschlagen.' + #13#10 +
           'Bitte manuell installieren: python.org/downloads',
           mbError, MB_OK);
  end else begin
    MsgBox('Python 3.11 wird benötigt.' + #13#10 +
           'Download: python.org/downloads',
           mbInformation, MB_OK);
  end;

  Result := False;
end;

{ Called after all files are copied }
procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
  App:  String;
begin
  if CurStep <> ssPostInstall then Exit;

  App := ExpandConstant('{app}');

  { Install Flask & PyWebView }
  WizardForm.StatusLabel.Caption := CustomMessage('InstallingDeps');
  Exec(PythonPath, '-m pip install flask pywebview --quiet',
    App, SW_HIDE, ewWaitUntilTerminated, Code);

  { Generate app icon }
  WizardForm.StatusLabel.Caption := CustomMessage('GeneratingIcon');
  Exec(PythonPath, '"' + App + '\icon.py"',
    App, SW_HIDE, ewWaitUntilTerminated, Code);
end;
