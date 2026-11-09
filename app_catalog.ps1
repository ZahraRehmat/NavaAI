$ErrorActionPreference = 'Stop'
$entries = @()
Get-StartApps | ForEach-Object { $entries += @{ name=$_.Name; kind='app'; target=$_.AppID } }
$roots = @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('CommonDesktopDirectory'), [Environment]::GetFolderPath('StartMenu'), [Environment]::GetFolderPath('CommonStartMenu'))
foreach ($root in $roots) {
    if (Test-Path -LiteralPath $root) {
        Get-ChildItem -LiteralPath $root -Filter '*.lnk' -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            $entries += @{name=$_.BaseName; kind='shortcut'; target=$_.FullName}
        }
    }
}
foreach ($reg in @('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths', 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths')) {
    if (Test-Path $reg) {
        Get-ChildItem $reg | ForEach-Object {
            $value = $_.GetValue('')
            if ($value) { $entries += @{name=$_.PSChildName.Replace('.exe','');kind='exe';target=$value.Trim('"')} }
        }
    }
}
ConvertTo-Json -InputObject @($entries) -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'apps.json') -Encoding UTF8
