# -*- coding: utf-8 -*-
"""
Upload videos to Modal Volume
上传视频到 Modal Volume
"""

import subprocess
import sys
from pathlib import Path


def upload_file(local_path: str, remote_subdir: str = "input"):
    """
    上传单个文件到 Modal Volume
    
    Args:
        local_path: 本地文件路径
        remote_subdir: Volume 中的子目录，默认 input
    """
    local_path = Path(local_path)
    
    if not local_path.exists():
        print(f"Error: File not found: {local_path}")
        return False
    
    remote_path = f"/{remote_subdir}/{local_path.name}"
    
    print(f"Uploading: {local_path} -> lada-videos:{remote_path}")
    
    cmd = [
        "modal", "volume", "put",
        "lada-videos",
        str(local_path),
        remote_path,
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"Done: {local_path.name}")
        return True
    else:
        print(f"Failed: {local_path.name}")
        return False


def upload_directory(local_dir: str, remote_subdir: str = "input"):
    """上传目录中的所有视频文件"""
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
        if upload_file(str(f), remote_subdir):
            success += 1
    
    print(f"\nUploaded: {success}/{len(files)}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python upload.py <file_or_directory>")
        print("  python upload.py video.mp4")
        print("  python upload.py ./videos/")
        return
    
    path = Path(sys.argv[1])
    
    if path.is_file():
        upload_file(str(path))
    elif path.is_dir():
        upload_directory(str(path))
    else:
        print(f"Error: Path not found: {path}")


if __name__ == "__main__":
    main()
