$ErrorActionPreference = 'Stop'
$overlayInstallRoot = Join-Path $env:ProgramFiles 'Gwen Accessibility'
$overlayResolvedRoot = [IO.Path]::GetFullPath($overlayInstallRoot)
if ($overlayResolvedRoot -ne [IO.Path]::GetFullPath((Join-Path $env:ProgramFiles 'Gwen Accessibility'))) { throw 'Unexpected install path.' }
$overlayMetaPath = Join-Path $overlayResolvedRoot 'install.json'
if (-not (Test-Path -LiteralPath $overlayMetaPath)) { throw 'No Gwen UIAccess installation record exists.' }
$overlayMeta = Get-Content -LiteralPath $overlayMetaPath -Raw | ConvertFrom-Json
if ($overlayMeta.thumbprint -notmatch '^[A-Fa-f0-9]{40}$' -or $overlayMeta.subject -ne 'CN=Gwen Local Accessibility Overlay') { throw 'Unexpected certificate identity.' }
foreach ($overlayStore in @('Root','TrustedPublisher','My')) {
    $overlayCertPath = 'Cert:\LocalMachine\' + $overlayStore + '\' + $overlayMeta.thumbprint
    $overlayCert = Get-Item -LiteralPath $overlayCertPath -ErrorAction SilentlyContinue
    if ($overlayCert) {
        if ($overlayCert.Subject -ne $overlayMeta.subject) { throw 'Certificate identity mismatch.' }
        Remove-Item -LiteralPath $overlayCertPath
    }
}
foreach ($overlayFileName in @('GwenOverlay.exe','overlay-public.cer','install.json','uninstall.ps1')) {
    $overlayFile = [IO.Path]::GetFullPath((Join-Path $overlayResolvedRoot $overlayFileName))
    if ([IO.Path]::GetDirectoryName($overlayFile) -ne $overlayResolvedRoot) { throw 'Unexpected removal path.' }
    if (Test-Path -LiteralPath $overlayFile) { Remove-Item -LiteralPath $overlayFile }
}
if (-not (Get-ChildItem -LiteralPath $overlayResolvedRoot -Force | Select-Object -First 1)) { Remove-Item -LiteralPath $overlayResolvedRoot }
Write-Output 'Removed the Gwen drawing helper and its installation-specific local certificate trust.'
