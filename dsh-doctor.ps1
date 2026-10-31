# dsh-doctor.ps1 —— DSH 桌面端起不来时的体检 + 止血脚本
# 用法：右键「用 PowerShell 运行」，或者：
#   powershell -ExecutionPolicy Bypass -File .\dsh-doctor.ps1
#   powershell -ExecutionPolicy Bypass -File .\dsh-doctor.ps1 -Profile desktop -Backup
#
# 它只做四件事：
#   1) 打印 profile 位置和当前插件清单
#   2) 找出「只出现在 dependencies 或只出现在 bundles」的插件（最常见的启动死因）
#   3) 找最新的 crash 日志，把「谁在等谁」那几行抠出来
#   4) -Backup 时把 package.json 备份成 .bak-时间戳
# 不改任何东西（除非你加 -Backup，那也只是复制一份）。

param(
    [string]$Profile = "desktop",
    [switch]$Backup
)

$ErrorActionPreference = "Stop"
$root = Join-Path $env:USERPROFILE ".dsh\profiles\$Profile"
$pkg = Join-Path $root "package.json"
$logDir = Join-Path $env:APPDATA "@deepseek-ai\dsh-desktop\logs"

Write-Host "== DSH 体检 ==" -ForegroundColor Cyan
Write-Host "profile : $root"
if (-not (Test-Path $pkg)) { throw "找不到 $pkg —— profile 名字对吗？" }

$j = Get-Content $pkg -Raw -Encoding utf8 | ConvertFrom-Json
$deps = @($j.dependencies.PSObject.Properties.Name)
$bundles = @($j.dsh.profile.bundles)

Write-Host ""
Write-Host "依赖 $($deps.Count) 个，启动清单 $($bundles.Count) 个"

# ---- 2) 两处对不上 = 启动就炸 ----
$onlyDep = $deps | Where-Object { $deps -and ($bundles -notcontains $_) }
$onlyBundle = $bundles | Where-Object { $_ -and ($deps -notcontains $_) -and ($_ -notlike "@deepseek-ai/*") }
if ($onlyDep) {
    Write-Host ""
    Write-Host "⚠ 只在 dependencies、不在启动清单（装了但没启）:" -ForegroundColor Yellow
    $onlyDep | ForEach-Object { Write-Host "   - $_" }
}
if ($onlyBundle) {
    Write-Host ""
    Write-Host "⚠ 只在启动清单、依赖里没有（很可能就是启动失败的原因）:" -ForegroundColor Red
    $onlyBundle | ForEach-Object { Write-Host "   - $_" }
}
if (-not $onlyDep -and -not $onlyBundle) {
    Write-Host "✓ 两处一致，插件清单本身没有问题" -ForegroundColor Green
}

# ---- 3) 最近的崩溃日志 ----
Write-Host ""
if (Test-Path $logDir) {
    $log = Get-ChildItem $logDir -Filter "crash-*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($log) {
        Write-Host "最近的崩溃日志：$($log.FullName)  ($($log.LastWriteTime))" -ForegroundColor Cyan
        $text = Get-Content $log.FullName -Raw -Encoding utf8
        $lines = $text -split "`r?`n"
        $hit = $lines | Where-Object { $_ -match 'did not activate|Missing services|waiting for services|^\s+\S+\s+.*tools|startup failed|Fatal' }
        if ($hit) { $hit | Select-Object -First 25 | ForEach-Object { Write-Host "   $_" } }
        Write-Host ""
        Write-Host "读法：required 插件在等某个服务（比如 tools）→ 说明提供那个服务的插件没起来；" -ForegroundColor DarkGray
        Write-Host "      不要修「等的人」，去找「本该提供服务、却没起来」的那个插件。" -ForegroundColor DarkGray
    } else {
        Write-Host "没找到崩溃日志（说明可能没崩过）。"
    }
} else {
    Write-Host "没有日志目录：$logDir"
}

# ---- 4) 备份 ----
if ($Backup) {
    $dst = "$pkg.bak-" + (Get-Date -Format "yyyyMMdd-HHmm")
    Copy-Item $pkg $dst -Force
    Write-Host ""
    Write-Host "已备份 → $dst" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "想留档就加 -Backup 再跑一次：会在改配置前把 package.json 复制成 .bak-时间戳。"
}

Write-Host ""
Write-Host "记住三件事：会话在 ~/.dsh/sessions（插件崩不影响它）；改完要彻底退出再开；起不来就换 dsh web 进来修。"
