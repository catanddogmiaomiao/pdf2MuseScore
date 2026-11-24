#ifndef AppVersion
  #define AppVersion "0.3.0"
#endif
#ifndef PayloadDir
  #define PayloadDir "..\dist\PDF2Muse"
#endif
#ifndef InstallerOutput
  #define InstallerOutput "..\dist"
#endif
[Setup]
AppId={{5EE64B89-4757-4EE0-90DD-B6D718F34B84}
AppName=PDF2Muse
AppVersion={#AppVersion}
AppPublisher=PDF2Muse
AppPublisherURL=https://pdf2muse.top
AppSupportURL=https://pdf2muse.top/legal/contact/
AppUpdatesURL=https://pdf2muse.top
DefaultDirName={localappdata}\Programs\PDF2Muse
DefaultGroupName=PDF2Muse
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.17763
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
InfoBeforeFile=..\legal\INSTALL-NOTICE.txt
OutputDir={#InstallerOutput}
OutputBaseFilename=PDF2Muse-{#AppVersion}-Windows-x64-Setup
SetupIconFile=..\assets\app-icon.ico
UninstallDisplayIcon={app}\PDF2Muse.exe
Compression=zip/9
SolidCompression=no
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayName=PDF2Muse
VersionInfoVersion={#AppVersion}
[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{group}\PDF2Muse"; Filename: "{app}\PDF2Muse.exe"
Name: "{group}\Legal documents"; Filename: "{app}\_internal\legal\index.html"
Name: "{autodesktop}\PDF2Muse"; Filename: "{app}\PDF2Muse.exe"; Tasks: desktopicon
[Run]
Filename: "{app}\PDF2Muse.exe"; Description: "Launch PDF2Muse"; Flags: nowait postinstall skipifsilent
; Uninstall deliberately preserves the user's score library, outputs and account settings.
