param(
    [Parameter(Mandatory = $true)]
    [string]$Name
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$template = Join-Path $root 'modules/_template'
$target = Join-Path $root "modules/$Name"

if (-not (Test-Path $template)) { Write-Error "找不到模板目录: $template" }
if (Test-Path $target) { Write-Error "模块已存在: $target" }

Copy-Item -Path $template -Destination $target -Recurse

$utf8 = New-Object System.Text.UTF8Encoding($false)
Get-ChildItem -Path $target -Recurse -Filter *.md | ForEach-Object {
    $content = [System.IO.File]::ReadAllText($_.FullName)
    $content = $content.Replace('<name>', $Name)
    [System.IO.File]::WriteAllText($_.FullName, $content, $utf8)
}

Write-Host "已创建模块: modules/$Name"
Write-Host "下一步："
Write-Host "  1. 填写 modules/$Name/MODULE.md 和 FLOW.md"
Write-Host "  2. 在 guardrails.yaml 登记（新增模块属于 R3，需要 ADR + 人批）"
