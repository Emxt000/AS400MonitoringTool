[Setup]
AppName=IBM i Native Ecosystem Dashboard
AppVersion=1.0.0
AppPublisher=IT Infrastructure
DefaultDirName={autopf}\IBMi_Dashboard
DefaultGroupName=IBM i Dashboard
OutputDir=Output
OutputBaseFilename=IBMi_Dashboard_Setup_v1.0.1
Compression=lzma2/max
SolidCompression=yes
SetupIconFile=logo.ico
UninstallDisplayIcon={app}\main.exe
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Pulls all compiled standalone files, DLLs, and embedded resources from Nuitka's main.dist folder
Source: "main.dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\IBM i Dashboard"; Filename: "{app}\main.exe"; IconFilename: "logo.ico"
Name: "{group}\Uninstall IBM i Dashboard"; Filename: "{uninstallexe}"
Name: "{autodesktop}\IBM i Dashboard"; Filename: "{app}\main.exe"; Tasks: desktopicon; IconFilename: "logo.ico"

[Run]
Filename: "{app}\main.exe"; Description: "{cm:LaunchProgram,IBM i Dashboard}"; Flags: nowait postinstall skipifsilent