$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$nexusPython = if ($env:NEXUS_BUILD_PYTHON) { $env:NEXUS_BUILD_PYTHON } else { Join-Path $PSScriptRoot '.venv\Scripts\python.exe' }
if (-not (Test-Path -LiteralPath $nexusPython)) {
    & (Join-Path $PSScriptRoot 'setup.ps1')
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $nexusPython)) {
        throw 'Python build environment setup failed'
    }
}
& $nexusPython -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
& $nexusPython tools/build_school_catalog.py
if ($LASTEXITCODE -ne 0) { throw 'School reference generation failed' }
& $nexusPython tools/build_knowledge.py
if ($LASTEXITCODE -ne 0) { throw 'Rule reference generation failed' }
# MT5's compiled extension imports NumPy through the C API; make that dependency
# visible to PyInstaller so its standard NumPy hook includes the native runtime.
$sslModule = & $nexusPython -c "import ssl; print(ssl.__file__)"
$sslDir = Split-Path -Parent $sslModule.Trim()
$tlsRuntimeData = @()
$runtimeDenylist = Join-Path $sslDir 'codex-rejected-cas.pem'
if (Test-Path -LiteralPath $runtimeDenylist) {
    $tlsRuntimeData = @('--add-data', ($runtimeDenylist + ';.'))
}
$pyinstallerArgs = @('--noconfirm', '--onedir', '--windowed', '--name', 'Quant Trading AI',
    '--paths', (Join-Path $PSScriptRoot 'src'),
    '--add-data', ((Join-Path $PSScriptRoot 'ui') + ';ui'),
    '--add-data', ((Join-Path $PSScriptRoot 'bridge') + ';bridge'),
    '--add-data', ((Join-Path $PSScriptRoot 'docs') + ';docs'),
    '--add-data', ((Join-Path $PSScriptRoot 'src') + ';src'),
    '--collect-all', 'webview', '--collect-all', 'MetaTrader5', '--collect-data', 'certifi',
    '--hidden-import', 'numpy', '--hidden-import', 'nexus.learning.proposals',
    '--hidden-import', 'nexus.learning.sandbox', '--hidden-import', 'nexus.learning.drift_monitor',
    '--distpath', 'Windows', '--workpath', 'build-work', '--specpath', 'build-work', 'launch.py')
if ($tlsRuntimeData.Count -gt 0) {
    $pyinstallerArgs += $tlsRuntimeData
}
& $nexusPython -m PyInstaller @pyinstallerArgs
if ($LASTEXITCODE -ne 0) { throw 'Windows build failed' }
