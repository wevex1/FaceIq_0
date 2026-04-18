param(
    [string]$FlutterCommand = "C:\flutter\bin\flutter.bat"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$flutterApp = Join-Path $repoRoot "flutter_app"

Push-Location $flutterApp
try {
    if (-not (Test-Path (Join-Path $flutterApp "windows"))) {
        & $FlutterCommand create --platforms=windows .
    }

    & $FlutterCommand pub get
    & $FlutterCommand run -d windows
}
finally {
    Pop-Location
}
