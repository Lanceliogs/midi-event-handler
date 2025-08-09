#define VERSION_FILE "version.txt"

#define VersionFileHandle FileOpen(AddBackslash(SourcePath) + VERSION_FILE)
#define MyVersion Trim(FileRead(VersionFileHandle))
#expr FileClose(VersionFileHandle)

[Setup]
AppName=MIDI Event Handler
AppVersion={#MyVersion}
AppId={{61E7BD3B-F815-4BA5-B8AD-AFF42431A546}
DefaultDirName={localappdata}\Programs\MIDI Event Handler
DefaultGroupName=MIDI Event Handler
UninstallDisplayIcon={app}\launcher.exe
OutputDir=dist\installer
OutputBaseFilename=midi-event-handler-setup_{#MyVersion}
SetupIconFile=meh-icon.ico
PrivilegesRequired=lowest
Compression=lzma
SolidCompression=yes
DisableWelcomePage=yes
DisableReadyPage=yes
DisableFinishedPage=no

[Files]
Source: "build\Release\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\MIDI Event Handler"; Filename: "{app}\launcher.exe"
Name: "{userprograms}\MIDI Event Handler"; Filename: "{app}\launcher.exe"

[Run]
Filename: "{app}\launcher.exe"; Description: "Launch MIDI Event Handler"; Flags: postinstall nowait skipifsilent
