param([string]$Compiler = '')
$ErrorActionPreference = 'Stop'
$installerProject = Split-Path -Parent $PSScriptRoot
$installerPython = Join-Path $installerProject '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $installerPython)) { throw 'Build machine needs the project Python 3.12 environment and its locked dependencies.' }
& $installerPython (Join-Path $PSScriptRoot 'build.py')
if ($LASTEXITCODE -ne 0) { throw 'Payload build failed.' }
if (-not $Compiler) {
    $installerCandidates = @((Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'), (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'), (Join-Path $env:USERPROFILE '.codex\tmp\nava-build-tools\InnoSetup\ISCC.exe'))
    $Compiler = $installerCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $Compiler) { throw 'Install the signed Inno Setup 6.7.4 compiler, or pass -Compiler with its ISCC.exe path. End users do not need this tool.' }
& $Compiler /Q (Join-Path $PSScriptRoot 'NavaAI.iss')
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
Write-Output ('Installer: ' + (Join-Path $installerProject 'dist\NAVA-AI-Setup-1.0.1-win-x64.exe'))
