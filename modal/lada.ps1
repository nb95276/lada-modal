#Requires -Version 7.0
# Lada Video Restore - Interactive CLI v1
# Modal serverless GPU video restoration

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Show-Menu {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Lada Video Restore (Modal GPU)" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1] Process from URL (Alist/Xiaoya)" -ForegroundColor Green
    Write-Host "  [2] Process local file" -ForegroundColor Green
    Write-Host "  [3] Batch process all" -ForegroundColor Green
    Write-Host "  [4] Split long video" -ForegroundColor Yellow
    Write-Host "  [5] Merge segments" -ForegroundColor Yellow
    Write-Host "  [6] List input files" -ForegroundColor Gray
    Write-Host "  [7] List output files" -ForegroundColor Gray
    Write-Host "  [8] Download results" -ForegroundColor Gray
    Write-Host "  [9] Upload video" -ForegroundColor Gray
    Write-Host "  [0] Exit" -ForegroundColor Red
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
}

function Get-Settings {
    Write-Host ""
    Write-Host "Settings (press Enter for defaults):" -ForegroundColor Cyan
    
    $detection = Read-Host "Detection model [fast/accurate] (default: fast)"
    if (-not $detection) { $detection = "fast" }
    
    $codec = Read-Host "Codec [h264_nvenc/hevc_nvenc/libx264/libx265] (default: h264_nvenc)"
    if (-not $codec) { $codec = "h264_nvenc" }
    
    $crf = Read-Host "Quality CRF [15-35] (default: 20)"
    if (-not $crf) { $crf = "20" }
    
    return @{
        Detection = $detection
        Codec = $codec
        CRF = $crf
    }
}

function Invoke-Modal {
    param([string[]]$Args)
    
    Push-Location $ScriptDir
    try {
        & .venv\Scripts\Activate.ps1
        & modal run lada_modal.py @Args
    }
    finally {
        Pop-Location
    }
}

function Process-FromUrl {
    Write-Host ""
    Write-Host "=== Process from URL ===" -ForegroundColor Cyan
    
    $url = Read-Host "Enter video URL"
    if (-not $url) {
        Write-Host "ERROR: URL is required" -ForegroundColor Red
        return
    }
    
    $settings = Get-Settings
    
    Write-Host ""
    Write-Host "Starting..." -ForegroundColor Green
    Invoke-Modal @(
        "--url", $url,
        "--detection", $settings.Detection,
        "--codec", $settings.Codec,
        "--crf", $settings.CRF
    )
}

function Process-LocalFile {
    Write-Host ""
    Write-Host "=== Process Local File ===" -ForegroundColor Cyan
    
    # List available files first
    Write-Host "Fetching input files..." -ForegroundColor Gray
    Invoke-Modal @("--action", "list-input")
    
    Write-Host ""
    $filename = Read-Host "Enter filename to process"
    if (-not $filename) {
        Write-Host "ERROR: Filename is required" -ForegroundColor Red
        return
    }
    
    $settings = Get-Settings
    
    Write-Host ""
    Write-Host "Starting..." -ForegroundColor Green
    Invoke-Modal @(
        "--filename", $filename,
        "--detection", $settings.Detection,
        "--codec", $settings.Codec,
        "--crf", $settings.CRF
    )
}

function Process-Batch {
    Write-Host ""
    Write-Host "=== Batch Process ===" -ForegroundColor Cyan
    
    $pattern = Read-Host "File pattern filter (leave empty for all)"
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
    Write-Host "Starting batch process..." -ForegroundColor Green
    Invoke-Modal $args
}

function Split-Video {
    Write-Host ""
    Write-Host "=== Split Long Video ===" -ForegroundColor Cyan
    
    # List available files
    Write-Host "Fetching input files..." -ForegroundColor Gray
    Invoke-Modal @("--action", "list-input")
    
    Write-Host ""
    $filename = Read-Host "Enter filename to split"
    if (-not $filename) {
        Write-Host "ERROR: Filename is required" -ForegroundColor Red
        return
    }
    
    $segment = Read-Host "Segment length in minutes (default: 10)"
    if (-not $segment) { $segment = "10" }
    
    Write-Host ""
    Write-Host "Splitting video..." -ForegroundColor Green
    Invoke-Modal @(
        "--action", "split",
        "--filename", $filename,
        "--segment", $segment
    )
}

function Merge-Segments {
    Write-Host ""
    Write-Host "=== Merge Segments ===" -ForegroundColor Cyan
    
    # List output files
    Write-Host "Fetching output files..." -ForegroundColor Gray
    Invoke-Modal @("--action", "list-output")
    
    Write-Host ""
    $prefix = Read-Host "Enter segment prefix (e.g., video_part)"
    if (-not $prefix) {
        Write-Host "ERROR: Prefix is required" -ForegroundColor Red
        return
    }
    
    $output = Read-Host "Output filename (default: merged.mp4)"
    if (-not $output) { $output = "merged.mp4" }
    
    Write-Host ""
    Write-Host "Merging segments..." -ForegroundColor Green
    Invoke-Modal @(
        "--action", "merge",
        "--prefix", $prefix,
        "--output", $output
    )
}

function List-InputFiles {
    Write-Host ""
    Write-Host "=== Input Files ===" -ForegroundColor Cyan
    Invoke-Modal @("--action", "list-input")
}

function List-OutputFiles {
    Write-Host ""
    Write-Host "=== Output Files ===" -ForegroundColor Cyan
    Invoke-Modal @("--action", "list-output")
}

function Download-Results {
    Write-Host ""
    Write-Host "=== Download Results ===" -ForegroundColor Cyan
    
    # List output files
    Invoke-Modal @("--action", "list-output")
    
    Write-Host ""
    Write-Host "[1] Download all" -ForegroundColor Green
    Write-Host "[2] Download specific file" -ForegroundColor Green
    $choice = Read-Host "Choice"
    
    Push-Location $ScriptDir
    try {
        & .venv\Scripts\Activate.ps1
        
        if ($choice -eq "1") {
            & python download.py all
        }
        elseif ($choice -eq "2") {
            $filename = Read-Host "Enter filename"
            & python download.py $filename
        }
    }
    finally {
        Pop-Location
    }
}

function Upload-Video {
    Write-Host ""
    Write-Host "=== Upload Video ===" -ForegroundColor Cyan
    
    $path = Read-Host "Enter file path (or drag file here)"
    $path = $path.Trim('"')
    
    if (-not (Test-Path $path)) {
        Write-Host "ERROR: File not found: $path" -ForegroundColor Red
        return
    }
    
    Push-Location $ScriptDir
    try {
        & .venv\Scripts\Activate.ps1
        & python upload.py $path
    }
    finally {
        Pop-Location
    }
}

# Main loop
while ($true) {
    Show-Menu
    $choice = Read-Host "Select option"
    
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
            Write-Host "Bye!" -ForegroundColor Cyan
            exit 0
        }
        default {
            Write-Host "Invalid option" -ForegroundColor Red
        }
    }
    
    Write-Host ""
    Read-Host "Press Enter to continue"
}
