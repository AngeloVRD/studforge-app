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
german.InstallingDeps=PyWebView wird installiert ...
english.InstallingDeps=Installing PyWebView ...

[Tasks]
Name: desktopicon; Description: "Verknüpfung auf dem Desktop erstellen"; \
  GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Nur der Client — der Server ist ein eigenes Programm auf dem Haupt-PC
; App launcher (tiny exe, no console window)
Source: "dist\Studforge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "main.py";   DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico";  DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#AppName}";                     Filename: "{app}\Studforge.exe"; \
  Comment: "Studforge 3D Manufaktur"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\Studforge.exe"; \
  IconFilename: "{app}\icon.ico"; Comment: "Studforge 3D Manufaktur"; Tasks: desktopicon

[Run]
; Offer to launch after install
Filename: "{app}\Studforge.exe"; \
  Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent

; ── Pascal Script ────────────────────────────────────────────────────────────
[Code]
var
  PythonPath: String;
  NeedPython: Boolean;

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

{ Called before the wizard appears — hier nur PRUEFEN, nicht installieren!
  WizardForm existiert hier noch NICHT, darf also nicht angefasst werden. }
function InitializeSetup(): Boolean;
var
  Answer: Integer;
begin
  Result := True;
  PythonPath := FindPython();
  NeedPython := (PythonPath = '');
  if not NeedPython then Exit;

  Answer := MsgBox(
    'Python 3.11 ist nicht installiert.' + #13#10 + #13#10 +
    'Soll Python jetzt automatisch mitinstalliert werden?' + #13#10 +
    '(ca. 25 MB, Internetverbindung erforderlich)',
    mbConfirmation, MB_YESNO);

  if Answer <> IDYES then begin
    MsgBox('Python 3.11 wird benötigt — Installation abgebrochen.' + #13#10 +
           'Download: python.org/downloads',
           mbInformation, MB_OK);
    Result := False;
  end;
  { Bei JA: NeedPython bleibt True, der Download passiert in PrepareToInstall }
end;

{ Läuft NACH dem Klick auf "Installieren" — hier existiert WizardForm.
  Ein nicht-leerer Rückgabewert bricht sauber mit Meldung ab (kein Absturz). }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  Tmp:  String;
  Code: Integer;
begin
  Result := '';
  if not NeedPython then Exit;

  WizardForm.StatusLabel.Caption := 'Python 3.11 wird heruntergeladen ...';
  Tmp := ExpandConstant('{tmp}\python-3.11.9-amd64.exe');

  if not Exec('powershell.exe',
      '-NoProfile -ExecutionPolicy Bypass -Command ' +
      '"Invoke-WebRequest -Uri ' +
      '''https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe''' +
      ' -OutFile ''' + Tmp + ''' -UseBasicParsing"',
      '', SW_HIDE, ewWaitUntilTerminated, Code) then
  begin
    Result := 'Python konnte nicht heruntergeladen werden.' + #13#10 +
              'Bitte Internetverbindung prüfen und Setup erneut starten.';
    Exit;
  end;

  if not FileExists(Tmp) then
  begin
    Result := 'Python-Download fehlgeschlagen. Bitte erneut versuchen.';
    Exit;
  end;

  WizardForm.StatusLabel.Caption := 'Python wird installiert (kann 1-2 Minuten dauern) ...';
  Exec(Tmp, '/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1',
       '', SW_HIDE, ewWaitUntilTerminated, Code);
  DeleteFile(Tmp);

  PythonPath := FindPython();
  if PythonPath = '' then
    Result := 'Python wurde installiert, aber nicht gefunden.' + #13#10 +
              'Bitte den PC neu starten und Setup erneut ausführen.';
end;

{ Called after all files are copied }
procedure CurStepChanged(CurStep: TSetupStep);
var
  Code: Integer;
  App:  String;
begin
  if CurStep <> ssPostInstall then Exit;

  if PythonPath = '' then PythonPath := FindPython();
  if PythonPath = '' then Exit;

  App := ExpandConstant('{app}');

  { Install PyWebView (Client braucht kein Flask — der Server rendert alles) }
  WizardForm.StatusLabel.Caption := CustomMessage('InstallingDeps');
  Exec(PythonPath, '-m pip install pywebview --quiet',
    App, SW_HIDE, ewWaitUntilTerminated, Code);
end;
