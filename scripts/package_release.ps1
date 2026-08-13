# Assemble the user-facing release folder: setup EXE + setup.txt (+ optional zip).
# Run after PyInstaller and Inno Setup, or when the installer EXE already exists.
param(
    [switch]$SkipZip
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$Version = (Select-String -Path "version.py" -Pattern 'APP_VERSION\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
$ExeName = "MultiVerse-Setup-$Version.exe"
$ExeSrc = Join-Path $Root "installer\output\$ExeName"
$SetupSrc = Join-Path $Root "installer\setup.txt"
$ReleaseDir = Join-Path $Root "release\MultiVerse-$Version"
$ZipPath = Join-Path $Root "release\MultiVerse-$Version.zip"

if (-not (Test-Path $ExeSrc)) {
    Write-Error "Missing installer: $ExeSrc`nBuild first: pyinstaller multiverse.spec --noconfirm; iscc installer\MultiVerse.iss"
}
if (-not (Test-Path $SetupSrc)) {
    Write-Error "Missing prerequisites file: $SetupSrc"
}

# Keep setup.txt version line in sync with version.py
$SetupText = Get-Content $SetupSrc -Raw
$SetupText = $SetupText -replace '(?m)^Version: .*$', "Version: $Version"
$SetupText = $SetupText -replace 'MultiVerse-Setup-[0-9.]+\.exe', $ExeName

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
Copy-Item -Force $ExeSrc (Join-Path $ReleaseDir $ExeName)
Set-Content -Path (Join-Path $ReleaseDir "setup.txt") -Value $SetupText.TrimEnd() -Encoding UTF8

Write-Host "Release folder: $ReleaseDir"
Write-Host "  $ExeName"
Write-Host "  setup.txt"

if (-not $SkipZip) {
    if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
    Compress-Archive -Path (Join-Path $ReleaseDir "*") -DestinationPath $ZipPath -Force
    Write-Host "Zip: $ZipPath"
}

Write-Host "Done."
