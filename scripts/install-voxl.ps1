# Install the pinned voxl-server crate (binary name: voxl) into HERMES_HOME.
# Native libraries on Windows come from vcpkg: x264, libyuv, opus.
# GitHub releases ship the crate, not a prebuilt binary.
# ASCII-only for Windows PowerShell 5.1.
param()
$ErrorActionPreference = "Stop"
$Version = "0.3.3"
if ($env:HERMES_HOME) {
  $Root = Join-Path $env:HERMES_HOME "runtime\voxl"
} else {
  $Root = Join-Path $env:USERPROFILE ".hermes\runtime\voxl"
}
New-Item -ItemType Directory -Force -Path $Root | Out-Null
& cargo install voxl-server --version $Version --locked --root $Root --force
if ($LASTEXITCODE -ne 0) {
  throw "cargo install voxl-server failed"
}
Write-Host "voxl installed under $Root\bin"
