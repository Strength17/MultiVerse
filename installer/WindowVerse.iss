; WindowVerse Inno Setup installer script
; Requires Inno Setup 6+ (iscc.exe on PATH)

#define MyAppName "WindowVerse"
#define MyAppVersion "0.0.1.1"
#define MyAppPublisher "Strength Awa"
#define MyAppURL "https://github.com/strength17/windowverse"
#define MyAppExeName "WindowVerse.exe"
#define BuildDir "..\\dist\\WindowVerse"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=WindowVerse-Setup-{#MyAppVersion}
SetupIconFile=..\assets\windowverse.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#BuildDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var
  UserData: String;
begin
  if CurStep = ssPostInstall then
  begin
    UserData := ExpandConstant('{userdocs}\WindowVerse\data');
    if not DirExists(UserData) then
      CreateDir(UserData);
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nBible databases and background images go in Documents\WindowVerse\data\ — see README_DATA.txt after install.
