#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: 潘高
LastEditors: 潘高
Date: 2023-04-03 17:42:32
LastEditTime: 2024-02-24 09:36:56
Description: 生成 .iss exe安装包配置文件，需要用到 InnoSetup 软件。
'''

import sys
import os
pyappDir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(pyappDir)
from config.config import Config
try:
    # 统一从项目根目录 logo.png 生成 Windows 使用的 .ico 图标
    from icon.generate_icons import generate_logo_icons
except Exception:
    generate_logo_icons = None

appName = Config.appName    # 应用名称（展示用）
appNameEN = Config.appNameEN    # 应用名称-英文（用于生成文件夹）
appVersion = Config.appVersion  # 应用版本号
appVersion = appVersion[1:]    # 去掉第一位V
appDeveloper = Config.appDeveloper  # 应用开发者
appBlogs = Config.appBlogs  # 个人博客
rootDir = os.path.dirname(pyappDir)

# 确保 InnoSetup 使用的 logo.ico 由根目录 logo.png 自动生成
if 'generate_logo_icons' in globals() and generate_logo_icons is not None:
    generate_logo_icons()

buildDir = os.path.join(rootDir, 'build').replace('\\', '/')
logoPath = os.path.join(rootDir, 'pyapp', 'icon', 'logo.ico').replace('\\', '/')
appISSID = Config.appISSID    # 安装包唯一GUID


# 获取配置文件内容
def getIss():
    return r'''
; 脚本由 Inno Setup 脚本向导 生成！
; 有关创建 Inno Setup 脚本文件的详细资料请查阅帮助文档！

#define MyAppName "''' + appName + r'''"
#define MyAppVersion "''' + appVersion + r'''"
#define MyAppFolderName "''' + appNameEN + r'''"
#define MyAppPublisher "''' + appDeveloper + r'''"
#define MyAppURL "''' + appBlogs + r'''"
#define MyAppExeName "''' + appName + r'''.exe"
#define MyAppAssocName MyAppName + " 文件"
#define MyAppAssocExt ".myp"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; 注: AppId的值为单独标识该应用程序。
; 不要为其他安装程序使用相同的AppId值。
; (若要生成新的 GUID，可在菜单中点击 "工具|生成 GUID"。)
AppId={{''' + appISSID + r'''}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
ChangesAssociations=yes
DisableProgramGroupPage=yes
; 移除以下行，以在管理安装模式下运行（为所有用户安装）。
PrivilegesRequired=lowest
OutputDir=''' + buildDir + r'''
OutputBaseFilename={#MyAppName}-V{#MyAppVersion}_Windows
SetupIconFile=''' + logoPath + r'''
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; 安装前关闭正在运行的程序
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartApplications=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "''' + buildDir + r'''\{#MyAppFolderName}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
; 注意: 不要在任何共享系统文件上使用"Flags: ignoreversion"

[Registry]
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocExt}\OpenWithProgids"; ValueType: string; ValueName: "{#MyAppAssocKey}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}"; ValueType: string; ValueName: ""; ValueData: "{#MyAppAssocName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKA; Subkey: "Software\Classes\{#MyAppAssocKey}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\Applications\{#MyAppExeName}\SupportedTypes"; ValueType: string; ValueName: ".myp"; ValueData: ""

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[InstallDelete]
; 安装前清理旧文件
Type: filesandordirs; Name: "{app}\*"

[Code]
function GetUninstallString(): String;
var
  sUnInstPath: String;
  sUnInstallString: String;
begin
  sUnInstPath := ExpandConstant('Software\Microsoft\Windows\CurrentVersion\Uninstall\{#emit SetupSetting("AppId")}_is1');
  sUnInstallString := '';
  if not RegQueryStringValue(HKLM, sUnInstPath, 'UninstallString', sUnInstallString) then
    RegQueryStringValue(HKCU, sUnInstPath, 'UninstallString', sUnInstallString);
  Result := sUnInstallString;
end;

function IsUpgrade(): Boolean;
begin
  Result := (GetUninstallString() <> '');
end;

function UnInstallOldVersion(): Integer;
var
  sUnInstallString: String;
  iResultCode: Integer;
begin
  Result := 0;
  sUnInstallString := GetUninstallString();
  if sUnInstallString <> '' then begin
    sUnInstallString := RemoveQuotes(sUnInstallString);
    if Exec(sUnInstallString, '/SILENT /NORESTART /SUPPRESSMSGBOXES', '', SW_HIDE, ewWaitUntilTerminated, iResultCode) then
      Result := 3
    else
      Result := 2;
  end else
    Result := 1;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep=ssInstall) then
  begin
    if (IsUpgrade()) then
    begin
      UnInstallOldVersion();
    end;
  end;
end;

'''


# 生成配置文件
issDir = os.path.dirname(__file__)
with open(os.path.join(issDir, 'InnoSetup.iss'), 'w+', encoding='utf-8-sig') as f:
    f.write(getIss())

