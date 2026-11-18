$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$registry = Join-Path $root 'guardrails.yaml'
$modulesDir = Join-Path $root 'modules'

if (-not (Test-Path $registry)) { Write-Error "找不到 guardrails.yaml: $registry" }
if (-not (Test-Path $modulesDir)) { Write-Error "找不到 modules 目录: $modulesDir" }

$registered = @(
    Select-String -Path $registry -Pattern '^\s*-\s*name:\s*(\S+)' |
        ForEach-Object { $_.Matches[0].Groups[1].Value.Trim('"', "'") }
)

$actual = @(
    Get-ChildItem -Path $modulesDir -Directory |
        Where-Object { $_.Name -ne '_template' } |
        Select-Object -ExpandProperty Name
)

$unregistered = @($actual | Where-Object { $registered -notcontains $_ })
$missing = @($registered | Where-Object { $actual -notcontains $_ })

if ($unregistered.Count -gt 0) {
    Write-Host "未登记模块：$($unregistered -join ', ')" -ForegroundColor Red
}
if ($missing.Count -gt 0) {
    Write-Host "登记但目录不存在：$($missing -join ', ')" -ForegroundColor Red
}

if ($unregistered.Count -gt 0 -or $missing.Count -gt 0) { exit 1 }

Write-Host "模块登记检查通过（$($actual.Count) 个模块）"
