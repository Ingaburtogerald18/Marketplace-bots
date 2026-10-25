; Instalador de Windows. Abrilo con Inno Setup (https://jrsoftware.org/isinfo.php) despues de construir_exe.bat.
[Setup]
AppName=Marketplace Bot
AppVersion=2.0.0
DefaultDirName={autopf}\Marketplace Bot
DefaultGroupName=Marketplace Bot
OutputDir=..\dist
OutputBaseFilename=MarketplaceBot-Setup-2.0.0
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\Marketplace Bot\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\Marketplace Bot"; Filename: "{app}\Marketplace Bot.exe"
Name: "{autodesktop}\Marketplace Bot"; Filename: "{app}\Marketplace Bot.exe"

[Run]
Filename: "{app}\Marketplace Bot.exe"; Description: "Abrir Marketplace Bot"; Flags: nowait postinstall skipifsilent
