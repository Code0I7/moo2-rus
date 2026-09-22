# Start the game for automated testing.
# Relative paths on purpose: the absolute ones contain spaces and Start-Process
# splits unquoted arguments. The test config goes last so its [sdl] settings win
# and its [autoexec] is the one DOSBox runs.
param([switch]$NoTestConf)
$root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Stop-Process -Name DOSBox -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 700
Push-Location $root
$cfgArgs = @('-conf', '150\dosbox-150.conf', '-conf', '150\dosbox.conf')
# the repository folder name, relative to the game folder
$proj = Split-Path (Split-Path $PSScriptRoot -Parent) -Leaf
if (-not $NoTestConf) { $cfgArgs += @('-conf', "$proj\tools\dosbox-test.conf") }
$p = Start-Process -FilePath 'DOSBOX\DOSBox.exe' -ArgumentList $cfgArgs -WorkingDirectory $root -PassThru
Pop-Location
Start-Sleep -Seconds 18
Write-Output "started pid=$($p.Id)  args: $($cfgArgs -join ' ')"
