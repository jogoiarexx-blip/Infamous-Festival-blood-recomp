# Script de Inicializacao Interativa - inFAMOUS: Festival of Blood
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$env:PS3_VFS_ROOT = Join-Path $scriptDir "private"
$env:GCM_COMPOSITE_RT = "0x00AB8000"

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Iniciando inFAMOUS: Festival of Blood Recomp (D3D12)  " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "VFS Root: $env:PS3_VFS_ROOT"
Write-Host "Composicao: $env:GCM_COMPOSITE_RT (3D Albedo / Texturas Ativas)"
Write-Host "Controles: XInput ativo para porta 0"
Write-Host ""

$exe = Join-Path $scriptDir "out\build\MyGameRecomp.exe"
$eboot = Join-Path $scriptDir "private\game\EBOOT.elf"

& $exe $eboot
