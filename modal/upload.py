# -*- coding: utf-8 -*-
"""
Upload videos to Modal Volume
"""

import subprocess
import sys
import os
from pathlib import Path

# Get modal.exe path from .venv312
SCRIPT_DIR = Path(__file__).parent
MODAL_EXE = SCRIPT_DIR / ".venv312" / "Scripts" / "modal.exe"


def activate_profile(profile: str):
    """Activate modal profile before operations"""
    if profile:
        subprocess.run([str(MODAL_EXE), "profile", "activate", profile], 
                      capture_output=True)


def upload_file(local_path: str, remote_subdir: str = "input", profile: str = None):
    """
    Upload single file to Modal Volume
    
    Args:
        local_path: Local file path
        remote_subdir: Volume subdirectory, default input
        profile: Modal profile name
    """
    local_path = Path(local_path)
    
    if not local_path.exists():
        print(f"Error: File not found: {local_path}")
        return False
    
    remote_path = f"/{remote_subdir}/{local_path.name}"
    
    print(f"Uploading: {local_path} -> lada-videos:{remote_path}")
    
    # Activate profile first
    activate_profile(profile)
    
    cmd = [str(MODAL_EXE), "volume", "put", "lada-videos", str(local_path), remote_path]
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"Done: {local_path.name}")
        return True
    else:
        print(f"Failed: {local_path.name}")
        return False


def upload_directory(local_dir: str, remote_subdir: str = "input", profile: str = None):
    """Upload all video files in directory"""
    local_dir = Path(local_dir)
    
    if not local_dir.is_dir():
        print(f"Error: Not a directory: {local_dir}")
        return
    
    video_extensions = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
    files = [f for f in local_dir.iterdir() if f.suffix.lower() in video_extensions]
    
    if not files:
        print(f"No video files found in: {local_dir}")
        return
    
    print(f"Found {len(files)} video files")
    
    success = 0
    for f in files:
        if upload_file(str(f), remote_subdir, profile):
            success += 1
    
    print(f"\nUploaded: {success}/{len(files)}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python upload.py <file_or_directory> [profile]")
        print("  python upload.py video.mp4 hcxsmyl")
        print("  python upload.py ./videos/ made54898")
        return
    
    path = Path(sys.argv[1])
    profile = sys.argv[2] if len(sys.argv) > 2 else None
    
    if path.is_file():
        upload_file(str(path), profile=profile)
    elif path.is_dir():
        upload_directory(str(path), profile=profile)
    else:
        print(f"Error: Path not found: {path}")


if __name__ == "__main__":
    main()
