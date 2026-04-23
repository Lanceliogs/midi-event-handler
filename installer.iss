#define VERSION_FILE "build\installer_version.txt"

#define VersionFileHandle FileOpen(AddBackslash(SourcePath) + VERSION_FILE)
#define MyVersion Trim(FileRead(VersionFileHandle))
#expr FileClose(VersionFileHandle)

[Setup]
AppName=MIDI Event Handler
AppVersion={#MyVersion}
AppId={{61E7BD3B-F815-4BA5-B8AD-AFF42431A546}
DefaultDirName={localappdata}\Programs\MIDI Event Handler
DefaultGroupName=MIDI Event Handler
UninstallDisplayIcon={app}\meh.exe
OutputDir=dist\installer
OutputBaseFilename=midi-event-handler-setup_{#MyVersion}
SetupIconFile=meh-icon.ico
PrivilegesRequired=lowest
Compression=lzma
SolidCompression=yes
DisableWelcomePage=yes
DisableReadyPage=yes
DisableFinishedPage=no
ChangesEnvironment=yes

[Files]
Source: "build\release\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{userdesktop}\MIDI Event Handler"; Filename: "{app}\meh.exe"; WorkingDir: "{app}"
Name: "{userprograms}\MIDI Event Handler"; Filename: "{app}\meh.exe"; WorkingDir: "{app}"

[Registry]
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\meh.exe"; WorkingDir: "{app}"; Description: "Launch MIDI Event Handler"; Flags: postinstall nowait skipifsilent

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;
