# -*- coding: utf-8 -*-
"""
Download restored videos from Modal Volume
"""

import subprocess
import sys
from pathlib import Path

# Get modal.exe path from .venv312
SCRIPT_DIR = Path(__file__).parent
MODAL_EXE = SCRIPT_DIR / ".venv312" / "Scripts" / "modal.exe"


def list_output_files():
    """List output files in Volume (sorted to match display order)"""
    import json
    
    cmd = [str(MODAL_EXE), "volume", "ls", "lada-videos", "/output", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Failed to list files")
        return []
    
    try:
        data = json.loads(result.stdout)
        # Get filenames and sort them to match Modal's display order
        files = sorted([item["Filename"] for item in data if item.get("Type") == "file"])
        return files
    except (json.JSONDecodeError, KeyError):
        return []


def download_file(filename: str, local_dir: str = "."):
    """
    下载单个文件
    
    Args:
        filename: Volume 中的文件名 (可能带 output/ 前缀)
        local_dir: 本地保存目录
    """
    local_dir = Path(local_dir)
    local_dir.mkdir(parents=True, exist_ok=True)
    
    # 处理路径：ls 返回的文件名可能带 output/ 前缀
    if filename.startswith("output/"):
        remote_path = filename
        local_filename = filename.replace("output/", "")
    else:
        remote_path = f"output/{filename}"
        local_filename = filename
    
    local_path = local_dir / local_filename
    
    print(f"Downloading: {remote_path}")
    
    cmd = [
        str(MODAL_EXE), "volume", "get",
        "lada-videos",
        remote_path,
        str(local_path),
        "--force",
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"Saved: {local_path}")
        return True
    else:
        print(f"Failed: {remote_path}")
        return False


def download_all(local_dir: str = "./output"):
    """下载所有输出文件"""
    files = list_output_files()
    
    if not files:
        print("No output files found")
        return
    
    print(f"Found {len(files)} files")
    
    success = 0
    for f in files:
        if download_file(f, local_dir):
            success += 1
    
    print(f"\nDownloaded: {success}/{len(files)}")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python download.py list          # List output files")
        print("  python download.py all           # Download all")
        print("  python download.py <filename>    # Download specific file")
        return
    
    action = sys.argv[1]
    
    if action == "list":
        files = list_output_files()
        print("Output files:")
        for f in files:
            print(f"  {f}")
    
    elif action == "all":
        local_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"
        download_all(local_dir)
    
    else:
        # Support numeric index selection
        filename = action
        if filename.isdigit():
            files = list_output_files()
            idx = int(filename) - 1
            if 0 <= idx < len(files):
                filename = files[idx]
                # Remove output/ prefix if present
                if filename.startswith("output/"):
                    filename = filename[7:]
                print(f"Selected: {filename}")
            else:
                print(f"Error: Invalid index {action}")
                return
        
        local_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        download_file(filename, local_dir)


if __name__ == "__main__":
    main()
