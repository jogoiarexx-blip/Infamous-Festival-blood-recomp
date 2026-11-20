@echo off
setlocal
cd /d "%~dp0"
set "PS3_VFS_ROOT=%CD%\private"
set "GCM_COMPOSITE_RT=0x00AB8000"
echo ========================================================
echo   Iniciando inFAMOUS: Festival of Blood Recomp (D3D12)
echo ========================================================
echo VFS Root: %PS3_VFS_ROOT%
echo Render Target Composicao: %GCM_COMPOSITE_RT%
echo Controle: Conecte seu controle Xbox ou PlayStation (DS4/DualSense)
echo.
"%CD%\out\build\MyGameRecomp.exe" "%CD%\private\game\EBOOT.elf"
pause
