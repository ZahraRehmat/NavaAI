# One-time administrator installation. Run only after the user approves.
$ErrorActionPreference = 'Stop'
$overlayIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
$overlayPrincipal = [Security.Principal.WindowsPrincipal]::new($overlayIdentity)
if (-not $overlayPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run this installer in an administrator PowerShell after approving the UIAccess setup.' }
& (Join-Path $PSScriptRoot 'build.ps1')
$overlayInstallRoot = Join-Path $env:ProgramFiles 'Gwen Accessibility'
$overlayInstallExe = Join-Path $overlayInstallRoot 'GwenOverlay.exe'
$overlaySubject = 'CN=Gwen Local Accessibility Overlay'
$overlayMetaPath = Join-Path $overlayInstallRoot 'install.json'
New-Item -ItemType Directory -Path $overlayInstallRoot -Force | Out-Null
$overlayCertificate = $null
if (Test-Path -LiteralPath $overlayMetaPath) {
    $overlayPrevious = Get-Content -LiteralPath $overlayMetaPath -Raw | ConvertFrom-Json
    if ($overlayPrevious.thumbprint -match '^[A-Fa-f0-9]{40}$') {
        $overlayCandidate = Get-Item -LiteralPath ('Cert:\LocalMachine\My\' + $overlayPrevious.thumbprint) -ErrorAction SilentlyContinue
        if ($overlayCandidate -and $overlayCandidate.Subject -eq $overlaySubject -and $overlayCandidate.HasPrivateKey) { $overlayCertificate = $overlayCandidate }
    }
}
if (-not $overlayCertificate) {
    $overlayCertificate = New-SelfSignedCertificate -Type CodeSigningCert -Subject $overlaySubject -CertStoreLocation 'Cert:\LocalMachine\My' -KeyAlgorithm RSA -KeyLength 3072 -KeyExportPolicy NonExportable -HashAlgorithm SHA256 -NotAfter (Get-Date).AddYears(3)
}
$overlayPublicPath = Join-Path $overlayInstallRoot 'overlay-public.cer'
Export-Certificate -Cert $overlayCertificate -FilePath $overlayPublicPath -Force | Out-Null
Import-Certificate -FilePath $overlayPublicPath -CertStoreLocation 'Cert:\LocalMachine\Root' | Out-Null
Import-Certificate -FilePath $overlayPublicPath -CertStoreLocation 'Cert:\LocalMachine\TrustedPublisher' | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'GwenOverlay.exe') -Destination $overlayInstallExe -Force
$overlaySignature = Set-AuthenticodeSignature -LiteralPath $overlayInstallExe -Certificate $overlayCertificate -HashAlgorithm SHA256
if ($overlaySignature.Status -ne 'Valid') { throw ('Overlay signature did not validate: ' + $overlaySignature.StatusMessage) }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'uninstall.ps1') -Destination (Join-Path $overlayInstallRoot 'uninstall.ps1') -Force
@{thumbprint=$overlayCertificate.Thumbprint;subject=$overlaySubject;exe_sha256=(Get-FileHash -LiteralPath $overlayInstallExe -Algorithm SHA256).Hash;installed_at=(Get-Date).ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath $overlayMetaPath -Encoding UTF8
Write-Output ('Installed signed drawing helper: ' + $overlayInstallExe)
Write-Output 'Restart Gwen and enable the grid. UIAccess is granted only to this helper; UAC policies are unchanged.'
