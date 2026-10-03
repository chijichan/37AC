# 今天有新图片的角色目录 —— 批量识别运行器（v2）
#
# 用法（在仓库根目录 C:\projects\37AC 执行）：
#   .\scripts\run_today.ps1                                预览全部（不动文件）
#   .\scripts\run_today.ps1 -Apply                         执行移动（建议先预览）
#   .\scripts\run_today.ps1 -Apply -Only 安守实里,白子        只跑指定几个
#   .\scripts\run_today.ps1 -Apply -Skip 七度雪乃           跳过已处理的
#   .\scripts\run_today.ps1 -Limit 30                      每个目录只处理前 30 张
#   .\scripts\run_today.ps1 -Detect                        启用 YOLO 检测裁剪（默认关闭）
#   .\scripts\run_today.ps1 -ShowKeep                      逐条打印『保留』的图（默认只给数量）
#   .\scripts\run_today.ps1 -Character 七度雪乃 -Apply       只跑单个目录（等价于直接调 batch_recognize.py）
#   .\scripts\run_today.ps1 -ListOnly                      只打印将要处理的目录清单，不识别
#
# 说明：
#   · 默认带 --no-detect（整图分类）：规避 ultralytics 的 'Cannot set version_counter for
#     inference tensor' 报错，且实测整图比 YOLO 裁剪更准（79.0% vs 71.3%）。
#   · 每个目录的输出同时写入 src\cli\saves\logs\recognize_today_<时间>.log
#   · 移出的图按『识别到的角色名』落到 D:\datasets\_tmp\<角色名>\（识别失败 → \未识别\）

param(
  [switch]$Apply,
  [int]$Limit = 0,
  [string[]]$Only = @(),
  [string[]]$Skip = @(),
  [string]$Character = '',
  [switch]$Detect,
  [switch]$ShowKeep,
  [switch]$ListOnly
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$names = @()
if ($Character -ne '') {
  $names = @($Character)
} else {
  $listFile = Join-Path $root '.dsh-scratch\today_folders.txt'
  if (-not (Test-Path $listFile)) { Write-Output "找不到目录清单: $listFile"; exit 1 }
  $names = Get-Content $listFile -Encoding UTF8 |
    Where-Object { $_.Trim() -ne '' -and $_.Trim() -ne '_amazing' } |
    ForEach-Object { $_.Trim() }
}
if ($Only.Count -gt 0) { $names = $names | Where-Object { $Only -contains $_ } }
if ($Skip.Count -gt 0) { $names = $names | Where-Object { $Skip -notcontains $_ } }
if ($names.Count -eq 0) { Write-Output '没有匹配的目录'; exit 0 }

if ($ListOnly) {
  Write-Output ("将处理 {0} 个目录:" -f $names.Count)
  $names | ForEach-Object { Write-Output ('  ' + $_) }
  exit 0
}

$logDir = Join-Path $root 'src\cli\saves\logs'    # 项目自己的日志目录，不在仓库根建 logs
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$log = Join-Path $logDir ('recognize_today_{0:yyyyMMdd_HHmmss}.log' -f (Get-Date))
$mode = if ($Apply) { '执行移动' } else { '预览' }
$detect = if ($Detect) { 'YOLO 检测裁剪（--detect）' } else { '整图分类（默认）' }
Write-Output ("共 {0} 个目录 | 模式: {1} | 识别: {2} | 日志: {3}" -f $names.Count, $mode, $detect, $log)

$i = 0
$failedDirs = @()
foreach ($name in $names) {
  $i++
  Write-Output ''
  Write-Output ("[{0}/{1}] {2}" -f $i, $names.Count, $name)
  $expect = $name -replace '[（(].*?[)）]\s*$', ''
  $cmdArgs = @('scripts\batch_recognize.py', '--character', $name)
  if ($expect -ne $name) { $cmdArgs += @('--expect', "蔚蓝档案/$expect") }
  if ($Detect) { $cmdArgs += '--detect' }
  if ($ShowKeep) { $cmdArgs += '--show-keep' }
  if ($Limit -gt 0) { $cmdArgs += @('--limit', "$Limit") }
  if ($Apply) { $cmdArgs += '--apply' }
  & python @cmdArgs 2>&1 | Tee-Object -FilePath $log -Append
  if ($LASTEXITCODE -ne 0) { $failedDirs += $name; Write-Output ("  [警告] {0} 退出码 {1}" -f $name, $LASTEXITCODE) }
}

Write-Output ''
Write-Output ("全部完成（{0} 个目录）。日志: {1}" -f $names.Count, $log)
if ($failedDirs.Count -gt 0) { Write-Output ("以下目录执行异常，请检查: " + ($failedDirs -join ', ')) }
if (-not $Apply) { Write-Output '提示：以上为预览。确认无误后加 -Apply 再跑一次即真正移动。' }
