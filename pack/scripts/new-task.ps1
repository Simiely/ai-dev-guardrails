param(
    [Parameter(Mandatory = $true)]
    [string]$Id,
    [Parameter(Mandatory = $true)]
    [string]$Title,
    [ValidateSet('R0', 'R1', 'R2', 'R3')]
    [string]$Tier = 'R1'
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root "specs/$Id"

if (Test-Path $target) { Write-Error "任务已存在: $target" }

$files = switch ($Tier) {
    'R0' { @('plan') }
    'R1' { @('intent', 'spec') }
    default { @('intent', 'spec', 'plan') }
}

New-Item -ItemType Directory -Path $target -Force | Out-Null

$utf8 = New-Object System.Text.UTF8Encoding($false)
$date = Get-Date -Format 'yyyy-MM-dd'

foreach ($f in $files) {
    $src = Join-Path $root "templates/$f.md"
    if (-not (Test-Path $src)) { Write-Error "找不到模板: $src" }
    $content = [System.IO.File]::ReadAllText($src)
    $content = $content.Replace('{{TITLE}}', $Title).Replace('{{ID}}', $Id).Replace('{{TIER}}', $Tier).Replace('{{DATE}}', $date)
    [System.IO.File]::WriteAllText((Join-Path $target "$f.md"), $content, $utf8)
}

Write-Host "已创建任务: specs/$Id ($Tier)"
Get-ChildItem $target | ForEach-Object { Write-Host "  - $($_.Name)" }
Write-Host "下一步：运行 guardrails brief --task specs/$Id，只加载它选中的章节。"
