$script = "lada_modal_v7_dev.py"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$venvPython = Join-Path $PSScriptRoot ".venv312\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    $venvPython = "python" # 回退到系统路径
}
# 定义运行命令：直接用虚拟环境的 python 运行模块
$m = "& `"$venvPython`" -m modal"

function Show-Menu {
    Clear-Host
    Write-Host "=== Lada Modal 视频修复工具 ===" -ForegroundColor Cyan
    Write-Host "1. 列出输入文件 (Volume: /input)"
    Write-Host "2. 开始修复视频 (并行模式)"
    Write-Host "3. 从 URL 下载并修复"
    Write-Host "4. 查看修复结果 (Volume: /output)"
    Write-Host "5. 登录 Modal 账号"
    Write-Host "Q. 退出"
    Write-Host "==============================="
    Write-Host "使用环境: $venvPython" -ForegroundColor DarkGray
}

while ($true) {
    Show-Menu
    $choice = Read-Host "请选择操作"
    switch ($choice) {
        "1" { Invoke-Expression "$m run $script --action input"; Pause }
        "2" {
            Write-Host "正在获取文件列表..."
            Invoke-Expression "$m run $script --action input"
            $idx = Read-Host "请输入要修复的文件编号"
            if ($idx) { Invoke-Expression "$m run $script --action parallel --filename $idx" }
            Pause
        }
        "3" {
            $url = Read-Host "请输入视频 URL"
            if ($url) {
                $para = Read-Host "是否开启并行模式? (y/n, 默认y)"
                if ($para -eq "n") { Invoke-Expression "$m run $script --action restore --url `"$url`"" }
                else { Invoke-Expression "$m run $script --action restore --url `"$url`" --parallel" }
            }
            Pause
        }
        "4" { Invoke-Expression "$m run $script --action output"; Pause }
        "5" { Invoke-Expression "$m setup"; Pause }
        "q" { exit }
        "Q" { exit }
    }
}
