$ErrorActionPreference = 'Stop'
$nexusRoot = $PSScriptRoot
Set-Location -LiteralPath $nexusRoot
if (-not (Test-Path -LiteralPath (Join-Path $nexusRoot '.venv\Scripts\python.exe'))) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 x64 مطلوب. يمكن استخدام حزمة Windows المبنية دون Python.' }
}
& '.\.venv\Scripts\python.exe' -m pip install --requirement requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'فشل تثبيت الاعتمادات؛ راجع اتصال الإنترنت والسجل.' }
Write-Host 'تم الإعداد. افتح Start-NEXUS.cmd.'
