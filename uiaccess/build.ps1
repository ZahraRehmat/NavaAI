$ErrorActionPreference = 'Stop'
$overlayCompiler = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $overlayCompiler)) { throw '.NET Framework C# compiler was not found.' }
$overlayBuildArgs = @('/nologo','/target:winexe','/optimize+',('/out:' + (Join-Path $PSScriptRoot 'GwenOverlay.exe')),('/win32manifest:' + (Join-Path $PSScriptRoot 'GwenOverlay.manifest')),'/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll','/reference:System.Web.Extensions.dll',(Join-Path $PSScriptRoot 'GwenOverlay.cs'))
& $overlayCompiler @overlayBuildArgs
if ($LASTEXITCODE -ne 0) { throw 'Overlay build failed.' }
Write-Output 'Built drawing-only UIAccess overlay. It is not installed or trusted yet.'
