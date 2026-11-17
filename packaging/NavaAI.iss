#ifndef PayloadDir
  #define PayloadDir "..\build\NAVA AI"
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif
[Setup]
AppId={{80B0A294-FA71-4BD5-9436-D778423B5301}
AppName=NAVA AI
AppVersion=1.0.1
AppPublisher=NAVA AI
DefaultDirName={localappdata}\Programs\NAVA AI
DefaultGroupName=NAVA AI
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.19041
OutputDir={#OutputDir}
OutputBaseFilename=NAVA-AI-Setup-1.0.1-win-x64
SetupIconFile=..\assets\nava.ico
UninstallDisplayIcon={app}\NAVA AI.exe
WizardStyle=modern dark
WizardSizePercent=110
WizardSmallImageFile=..\assets\installer-logo.bmp
Compression=lzma2/fast
SolidCompression=yes
LZMAUseSeparateProcess=yes
DisableProgramGroupPage=yes
DisableWelcomePage=no
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "autostart"; Description: "Start NAVA AI automatically after Windows sign-in (Say Nava listen)"; Flags: checkedonce
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: checkedonce
[Files]
; Settings exclusions apply only to the root, never nested runtime configs.
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Excludes: "voice_config.json,command_help_config.json,smart_grid_config.json,aliases.json,label_aliases.json,website_aliases.json,config.json,apps.json"; Flags: ignoreversion
Source: "{#PayloadDir}\models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\browsers\*"; DestDir: "{app}\browsers"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#PayloadDir}\voice_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#PayloadDir}\command_help_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#PayloadDir}\smart_grid_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#PayloadDir}\aliases.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#PayloadDir}\config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#PayloadDir}\label_aliases.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#PayloadDir}\website_aliases.json"; DestDir: "{app}"; Flags: onlyifdoesntexist uninsneveruninstall
[Icons]
Name: "{autoprograms}\NAVA AI"; Filename: "{app}\NAVA AI.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\nava.ico"
Name: "{autodesktop}\NAVA AI"; Filename: "{app}\NAVA AI.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\nava.ico"; Tasks: desktopicon
Name: "{userstartup}\NAVA AI"; Filename: "{app}\NAVA AI.exe"; Parameters: "--startup"; WorkingDir: "{app}"; IconFilename: "{app}\assets\nava.ico"; Tasks: autostart
[Run]
Filename: "{app}\NAVA AI.exe"; Parameters: "--startup"; Description: "Start NAVA AI — ready for Nava listen"; Flags: nowait postinstall skipifsilent
[Code]
procedure CurStepChanged(CurStep: TSetupStep);
var ResultCode: Integer;
begin
  if CurStep = ssPostInstall then begin
    WizardForm.StatusLabel.Caption := 'Discovering your apps and preparing offline controls...';
    if not Exec(ExpandConstant('{app}\NAVA AI.exe'), '--initialize', ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      RaiseException('NAVA AI could not finish initialization. Please run Setup again.');
    if ResultCode <> 0 then
      RaiseException('NAVA AI setup checks failed. Details: ' + ExpandConstant('{app}\logs\launch-error.txt'));
  end;
end;
