; Include the Modern UI 2 Header File
!include "MUI2.nsh"

; The name of the installer
Name "SPIR-V Toolchain"

; The filename of the installer
OutFile "spirv-toolchain-win32.exe"

; The default installation directory
InstallDir $PROGRAMFILES\SPIR-V

; Request application privileges for Windows Vista and above
RequestExecutionLevel admin

; Default Settings
ShowInstDetails show
ShowUninstDetails show

;--------------------------------

; Installer Pages
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Version Settings
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "SPIR-V Toolchain Installer"
VIAddVersionKey /LANG=${LANG_ENGLISH} "Comments" "SPIR-V Toolchain Installer"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" ""
VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright" ""
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "SPIR-V Toolchain Installer"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "0.0.0.0"
VIProductVersion "0.0.0.0"

;--------------------------------

; Uninstaller instructions
Section "Uninstall"

    ; No reboot required
    SetRebootFlag false
    
    ; Remove the wrappers directory from the system PATH
    Exec `powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'Machine').Replace(';$INSTDIR\wrappers', ''), 'Machine');"`
    
    ; Delete the installation directory
    RMDir /r $INSTDIR

SectionEnd

; Installer instructions
Section ""

    ; Set output path to the installation directory.
    SetOutPath $INSTDIR
    
    ; Install the executables
    File /r spirv
    File /r wrappers
    
    ; Write the uninstaller
    WriteUninstaller $INSTDIR\uninstall.exe
    
    ; Add the wrappers directory to the system PATH
    Exec `powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';$INSTDIR\wrappers', 'Machine');"`
    
SectionEnd
