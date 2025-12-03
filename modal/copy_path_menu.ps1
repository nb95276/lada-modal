#Requires -Version 7.0
# Add "Copy Full Path" to Windows right-click context menu v1
# Run as Administrator

$ErrorActionPreference = "Stop"

function Install-CopyPathMenu {
    Write-Host "Installing 'Copy Full Path' context menu..." -ForegroundColor Cyan
    
    # For files
    $fileKey = "HKCR:\*\shell\CopyFullPath"
    $fileCmd = "$fileKey\command"
    
    # For folders
    $folderKey = "HKCR:\Directory\shell\CopyFullPath"
    $folderCmd = "$folderKey\command"
    
    # For folder background
    $bgKey = "HKCR:\Directory\Background\shell\CopyFullPath"
    $bgCmd = "$bgKey\command"
    
    try {
        # Create HKCR drive if not exists
        if (-not (Test-Path "HKCR:")) {
            New-PSDrive -Name HKCR -PSProvider Registry -Root HKEY_CLASSES_ROOT | Out-Null
        }
        
        # Files
        New-Item -Path $fileKey -Force | Out-Null
        Set-ItemProperty -Path $fileKey -Name "(Default)" -Value "Copy Full Path"
        Set-ItemProperty -Path $fileKey -Name "Icon" -Value "shell32.dll,134"
        New-Item -Path $fileCmd -Force | Out-Null
        Set-ItemProperty -Path $fileCmd -Name "(Default)" -Value 'powershell -NoProfile -Command "Set-Clipboard -Value \"%1\""'
        
        # Folders
        New-Item -Path $folderKey -Force | Out-Null
        Set-ItemProperty -Path $folderKey -Name "(Default)" -Value "Copy Full Path"
        Set-ItemProperty -Path $folderKey -Name "Icon" -Value "shell32.dll,134"
        New-Item -Path $folderCmd -Force | Out-Null
        Set-ItemProperty -Path $folderCmd -Name "(Default)" -Value 'powershell -NoProfile -Command "Set-Clipboard -Value \"%1\""'
        
        # Folder background (current folder)
        New-Item -Path $bgKey -Force | Out-Null
        Set-ItemProperty -Path $bgKey -Name "(Default)" -Value "Copy Folder Path"
        Set-ItemProperty -Path $bgKey -Name "Icon" -Value "shell32.dll,134"
        New-Item -Path $bgCmd -Force | Out-Null
        Set-ItemProperty -Path $bgCmd -Name "(Default)" -Value 'powershell -NoProfile -Command "Set-Clipboard -Value \"%V\""'
        
        Write-Host "SUCCESS: Context menu installed" -ForegroundColor Green
        Write-Host ""
        Write-Host "Right-click any file/folder to see 'Copy Full Path'" -ForegroundColor Gray
    }
    catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
        Write-Host "Make sure to run as Administrator" -ForegroundColor Yellow
    }
}

function Uninstall-CopyPathMenu {
    Write-Host "Removing 'Copy Full Path' context menu..." -ForegroundColor Cyan
    
    try {
        if (-not (Test-Path "HKCR:")) {
            New-PSDrive -Name HKCR -PSProvider Registry -Root HKEY_CLASSES_ROOT | Out-Null
        }
        
        Remove-Item -Path "HKCR:\*\shell\CopyFullPath" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "HKCR:\Directory\shell\CopyFullPath" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "HKCR:\Directory\Background\shell\CopyFullPath" -Recurse -Force -ErrorAction SilentlyContinue
        
        Write-Host "SUCCESS: Context menu removed" -ForegroundColor Green
    }
    catch {
        Write-Host "ERROR: $_" -ForegroundColor Red
    }
}

# Main
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Copy Full Path - Context Menu Setup" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1] Install (add to right-click menu)" -ForegroundColor Green
Write-Host "[2] Uninstall (remove from menu)" -ForegroundColor Yellow
Write-Host "[0] Exit" -ForegroundColor Gray
Write-Host ""

$choice = Read-Host "Select option"

switch ($choice) {
    "1" { Install-CopyPathMenu }
    "2" { Uninstall-CopyPathMenu }
    "0" { exit 0 }
    default { Write-Host "Invalid option" -ForegroundColor Red }
}

Write-Host ""
Read-Host "Press Enter to exit"
