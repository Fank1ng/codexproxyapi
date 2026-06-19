#define MyAppName "the little dachshund"
#ifndef MyAppVersion
#define MyAppVersion "0.6.8"
#endif
#ifndef SourceDir
#define SourceDir "dist\windows"
#endif

[Setup]
AppId={{3E03DE59-0765-4F23-A285-9D9FB7DD06AF}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=fank1ng
DefaultDirName={localappdata}\Programs\the little dachshund
DefaultGroupName=the little dachshund
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Compression=lzma2
SolidCompression=yes
OutputDir=..\dist
OutputBaseFilename=the-little-dachshund-{#MyAppVersion}-win-x64
UninstallDisplayIcon={app}\the little dachshund.exe

[Files]
Source: "{#SourceDir}\the little dachshund.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\CodexProxyService.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\runtime\*"; DestDir: "{app}\runtime"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\the little dachshund"; Filename: "{app}\the little dachshund.exe"
Name: "{autodesktop}\the little dachshund"; Filename: "{app}\the little dachshund.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Run]
Filename: "{app}\CodexProxyService.exe"; Parameters: "--install"; Flags: runhidden waituntilterminated
Filename: "{app}\the little dachshund.exe"; Description: "Launch the little dachshund"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\CodexProxyService.exe"; Parameters: "--uninstall"; Flags: runhidden waituntilterminated
