#Requires -Version 7.0
# Lada 视频修复 - 交互式命令行 v1
# Modal 云端 GPU 视频修复工具

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Menu {
    Clear-Host
    Write-Host ""
    Write-Host "  ╭─────────────────────────────────────╮" -ForegroundColor DarkGray
    Write-Host "  │  " -ForegroundColor DarkGray -NoNewline
    Write-Host "Lada 视频修复" -ForegroundColor Magenta -NoNewline
    Write-Host " · Modal 云端GPU" -ForegroundColor DarkGray -NoNewline
    Write-Host "    │" -ForegroundColor DarkGray
    Write-Host "  ╰─────────────────────────────────────╯" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  处理" -ForegroundColor DarkGray
    Write-Host "    1  " -ForegroundColor Blue -NoNewline
    Write-Host "从链接处理 (小雅/Alist)" -ForegroundColor White
    Write-Host "    2  " -ForegroundColor Blue -NoNewline
    Write-Host "处理已上传的视频" -ForegroundColor White
    Write-Host "    3  " -ForegroundColor Blue -NoNewline
    Write-Host "批量处理所有视频" -ForegroundColor White
    Write-Host ""
    Write-Host "  工具" -ForegroundColor DarkGray
    Write-Host "    4  " -ForegroundColor Magenta -NoNewline
    Write-Host "切割长视频" -ForegroundColor White
    Write-Host "    5  " -ForegroundColor Magenta -NoNewline
    Write-Host "合并分段视频" -ForegroundColor White
    Write-Host ""
    Write-Host "  文件" -ForegroundColor DarkGray
    Write-Host "    6  " -ForegroundColor DarkCyan -NoNewline
    Write-Host "查看待处理文件" -ForegroundColor Gray
    Write-Host "    7  " -ForegroundColor DarkCyan -NoNewline
    Write-Host "查看已完成文件" -ForegroundColor Gray
    Write-Host "    8  " -ForegroundColor DarkCyan -NoNewline
    Write-Host "下载处理结果" -ForegroundColor Gray
    Write-Host "    9  " -ForegroundColor DarkCyan -NoNewline
    Write-Host "上传视频文件" -ForegroundColor Gray
    Write-Host ""
    Write-Host "    0  " -ForegroundColor DarkRed -NoNewline
    Write-Host "退出" -ForegroundColor DarkGray
    Write-Host ""
}

function Get-Settings {
    Write-Host ""
    Write-Host "  参数设置 " -ForegroundColor Magenta -NoNewline
    Write-Host "(直接回车使用默认值)" -ForegroundColor DarkGray
    Write-Host ""
    
    Write-Host "  检测模型 " -ForegroundColor White -NoNewline
    Write-Host "[fast/accurate]" -ForegroundColor DarkGray -NoNewline
    Write-Host " (fast): " -ForegroundColor DarkGray -NoNewline
    $detection = Read-Host
    if (-not $detection) { $detection = "fast" }
    
    Write-Host "  编码器 " -ForegroundColor White -NoNewline
    Write-Host "[h264_nvenc/hevc_nvenc]" -ForegroundColor DarkGray -NoNewline
    Write-Host " (h264_nvenc): " -ForegroundColor DarkGray -NoNewline
    $codec = Read-Host
    if (-not $codec) { $codec = "h264_nvenc" }
    
    Write-Host "  画质 CRF " -ForegroundColor White -NoNewline
    Write-Host "[15-35, 越小越好]" -ForegroundColor DarkGray -NoNewline
    Write-Host " (20): " -ForegroundColor DarkGray -NoNewline
    $crf = Read-Host
    if (-not $crf) { $crf = "20" }
    
    return @{
        Detection = $detection
        Codec = $codec
        CRF = $crf
    }
}

function Invoke-Modal {
    param([string[]]$ModalArgs)
    
    Push-Location $ScriptDir
    try {
        & .venv\Scripts\Activate.ps1
        Write-Host "  [DEBUG] modal run lada_modal.py $($ModalArgs -join ' ')" -ForegroundColor DarkYellow
        & modal run lada_modal.py @ModalArgs
    }
    finally {
        Pop-Location
    }
}

function Process-FromUrl {
    Write-Host ""
    Write-Host "  从链接处理视频" -ForegroundColor Magenta
    Write-Host "  支持: 小雅直链、Alist直链、任意视频直链" -ForegroundColor DarkGray
    Write-Host ""
    
    Write-Host "  视频链接: " -ForegroundColor White -NoNewline
    $url = Read-Host
    if (-not $url) {
        Write-Host "  ✗ 链接不能为空" -ForegroundColor Red
        return
    }
    
    $settings = Get-Settings
    
    Write-Host ""
    Write-Host "  ▶ 开始处理..." -ForegroundColor Blue
    Write-Host "  视频将在云端下载并处理" -ForegroundColor DarkGray
    Write-Host ""
    Invoke-Modal @(
        "--url", $url,
        "--detection", $settings.Detection,
        "--codec", $settings.Codec,
        "--crf", $settings.CRF
    )
}

function Process-LocalFile {
    Write-Host ""
    Write-Host "  处理已上传的视频" -ForegroundColor Magenta
    Write-Host ""
    
    Write-Host "  正在获取文件列表..." -ForegroundColor DarkGray
    Invoke-Modal @("--action", "input")
    
    Write-Host ""
    Write-Host "  文件名: " -ForegroundColor White -NoNewline
    $filename = Read-Host
    if (-not $filename) {
        Write-Host "  ✗ 文件名不能为空" -ForegroundColor Red
        return
    }
    
    $settings = Get-Settings
    
    Write-Host ""
    Write-Host "  ▶ 开始处理..." -ForegroundColor Blue
    Write-Host ""
    Invoke-Modal @(
        "--filename", $filename,
        "--detection", $settings.Detection,
        "--codec", $settings.Codec,
        "--crf", $settings.CRF
    )
}

function Process-Batch {
    Write-Host ""
    Write-Host "  批量处理" -ForegroundColor Magenta
    Write-Host "  自动跳过已处理的文件" -ForegroundColor DarkGray
    Write-Host ""
    
    Write-Host "  文件名过滤 " -ForegroundColor White -NoNewline
    Write-Host "(留空处理全部): " -ForegroundColor DarkGray -NoNewline
    $pattern = Read-Host
    $settings = Get-Settings
    
    $args = @(
        "--action", "batch",
        "--detection", $settings.Detection,
        "--codec", $settings.Codec,
        "--crf", $settings.CRF
    )
    
    if ($pattern) {
        $args += @("--pattern", $pattern)
    }
    
    Write-Host ""
    Write-Host "  ▶ 开始批量处理..." -ForegroundColor Blue
    Write-Host ""
    Invoke-Modal $args
}

function Split-Video {
    Write-Host ""
    Write-Host "  切割长视频" -ForegroundColor Magenta
    Write-Host "  将长视频切成小段，方便断点续传" -ForegroundColor DarkGray
    Write-Host ""
    
    Write-Host "  正在获取文件列表..." -ForegroundColor DarkGray
    Invoke-Modal @("--action", "input")
    
    Write-Host ""
    Write-Host "  文件名: " -ForegroundColor White -NoNewline
    $filename = Read-Host
    if (-not $filename) {
        Write-Host "  ✗ 文件名不能为空" -ForegroundColor Red
        return
    }
    
    Write-Host "  每段时长(分钟) " -ForegroundColor White -NoNewline
    Write-Host "(10): " -ForegroundColor DarkGray -NoNewline
    $segment = Read-Host
    if (-not $segment) { $segment = "10" }
    
    Write-Host ""
    Write-Host "  ▶ 正在切割视频..." -ForegroundColor Blue
    Write-Host ""
    Invoke-Modal @(
        "--action", "split",
        "--filename", $filename,
        "--segment", $segment
    )
    
    Write-Host ""
    Write-Host "  ℹ 切割完成后，可以用 [3] 批量处理所有分段" -ForegroundColor DarkCyan
}

function Merge-Segments {
    Write-Host ""
    Write-Host "  合并分段视频" -ForegroundColor Magenta
    Write-Host "  将处理完的分段合并成完整视频" -ForegroundColor DarkGray
    Write-Host ""
    
    Write-Host "  正在获取已完成文件..." -ForegroundColor DarkGray
    Invoke-Modal @("--action", "output")
    
    Write-Host ""
    Write-Host "  分段文件前缀 " -ForegroundColor White -NoNewline
    Write-Host "(如: video_part): " -ForegroundColor DarkGray -NoNewline
    $prefix = Read-Host
    if (-not $prefix) {
        Write-Host "  ✗ 前缀不能为空" -ForegroundColor Red
        return
    }
    
    Write-Host "  输出文件名 " -ForegroundColor White -NoNewline
    Write-Host "(merged.mp4): " -ForegroundColor DarkGray -NoNewline
    $output = Read-Host
    if (-not $output) { $output = "merged.mp4" }
    
    Write-Host ""
    Write-Host "  ▶ 正在合并分段..." -ForegroundColor Blue
    Write-Host ""
    Invoke-Modal @(
        "--action", "merge",
        "--prefix", $prefix,
        "--output", $output
    )
}

function List-InputFiles {
    Write-Host ""
    Write-Host "  待处理文件" -ForegroundColor Magenta
    Write-Host ""
    Invoke-Modal @("--action", "input")
}

function List-OutputFiles {
    Write-Host ""
    Write-Host "  已完成文件" -ForegroundColor Magenta
    Write-Host ""
    Invoke-Modal @("--action", "output")
}

function Download-Results {
    Write-Host ""
    Write-Host "  下载处理结果" -ForegroundColor Magenta
    Write-Host ""
    
    Invoke-Modal @("--action", "output")
    
    Write-Host ""
    Write-Host "    1  " -ForegroundColor Blue -NoNewline
    Write-Host "下载全部" -ForegroundColor White
    Write-Host "    2  " -ForegroundColor Blue -NoNewline
    Write-Host "下载指定文件" -ForegroundColor White
    Write-Host ""
    Write-Host "  选择: " -ForegroundColor White -NoNewline
    $choice = Read-Host
    
    Push-Location $ScriptDir
    try {
        & .venv\Scripts\Activate.ps1
        
        if ($choice -eq "1") {
            Write-Host ""
            Write-Host "  ▶ 正在下载所有文件..." -ForegroundColor Blue
            & python download.py all
        }
        elseif ($choice -eq "2") {
            Write-Host "  文件名: " -ForegroundColor White -NoNewline
            $filename = Read-Host
            Write-Host ""
            Write-Host "  ▶ 正在下载..." -ForegroundColor Blue
            & python download.py $filename
        }
    }
    finally {
        Pop-Location
    }
}

function Upload-Video {
    Write-Host ""
    Write-Host "  上传视频文件" -ForegroundColor Magenta
    Write-Host "  可以直接拖拽文件到窗口" -ForegroundColor DarkGray
    Write-Host ""
    
    Write-Host "  文件路径: " -ForegroundColor White -NoNewline
    $path = Read-Host
    $path = $path.Trim('"')
    
    if (-not (Test-Path $path)) {
        Write-Host "  ✗ 文件不存在: $path" -ForegroundColor Red
        return
    }
    
    Push-Location $ScriptDir
    try {
        & .venv\Scripts\Activate.ps1
        Write-Host ""
        Write-Host "  ▶ 正在上传..." -ForegroundColor Blue
        & python upload.py $path
    }
    finally {
        Pop-Location
    }
}

# 主循环
while ($true) {
    Show-Menu
    Write-Host "  > " -ForegroundColor Blue -NoNewline
    $choice = Read-Host
    
    switch ($choice) {
        "1" { Process-FromUrl }
        "2" { Process-LocalFile }
        "3" { Process-Batch }
        "4" { Split-Video }
        "5" { Merge-Segments }
        "6" { List-InputFiles }
        "7" { List-OutputFiles }
        "8" { Download-Results }
        "9" { Upload-Video }
        "0" { 
            Write-Host ""
            Write-Host "  再见!" -ForegroundColor Magenta
            Write-Host ""
            exit 0
        }
        default {
            Write-Host "  ✗ 无效选项" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Write-Host "  按回车键继续..." -ForegroundColor DarkGray -NoNewline
    Read-Host
}
