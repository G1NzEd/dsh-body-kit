# 装到本机（Windows）：建两个定时任务，缺 python 依赖就装上
# 用法：右键 → 用 PowerShell 运行；或者在 PowerShell 里：
#   cd <这个目录>; powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = 'Stop'
$kit = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "套件目录：$kit"

# 1) 找 python
$py = $null
foreach ($c in @('py','python','python3')) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd) { $py = $cmd.Source; break }
}
if (-not $py) { throw "没找到 Python。先装 Python 3.10+（勾选 Add to PATH）再跑一次。" }
Write-Host "Python：$py"

# 2) 依赖
& $py -c "import zstandard" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "装 zstandard …"
    & $py -m pip install --quiet zstandard
}

# 3) 第一次跑一遍，确认能读出会话
& $py (Join-Path $kit 'merge_flow.py') --dry-run

# 4) 建定时任务（每 5 分钟并流水，每 30 分钟写状态）
$pyw = $py
$merge = Join-Path $kit 'merge_flow.py'
$state = Join-Path $kit 'make_state.py'
schtasks /create /f /tn "dsh-body-merge" /sc minute /mo 5  /tr "`"$pyw`" `"$merge`"" | Out-Null
schtasks /create /f /tn "dsh-body-state" /sc minute /mo 30 /tr "`"$pyw`" `"$state`"" | Out-Null

Write-Host ""
Write-Host "装好了。以后每 5 分钟自动把各会话并进流水，每 30 分钟刷新一次 状态.md。"
Write-Host "想立刻看效果：  & `"$pyw`" `"$merge`"; & `"$pyw`" `"$state`""
