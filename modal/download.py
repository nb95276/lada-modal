# -*- coding: utf-8 -*-
"""
Download restored videos from Modal Volume
从 Modal Volume 下载修复后的视频
"""

import subprocess
import sys
from pathlib import Path


def list_output_files():
    """列出 Volume 中的输出文件"""
    import json
    
    # 使用 JSON 输出获取完整文件名
    cmd = ["modal", "volume", "ls", "lada-videos", "/output", "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("Failed to list files")
        return []
    
    try:
        data = json.loads(result.stdout)
        files = [item["Filename"] for item in data if item.get("Type") == "file"]
        return files
    except (json.JSONDecodeError, KeyError):
        # 回退到解析表格输出
        import re
        files = []
        for line in result.stdout.split("\n"):
            match = re.search(r"│\s*(output/[^\s│]+)", line)
            if match:
                filename = match.group(1).strip().rstrip("…")
                files.append(filename)
        return files


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
        "modal", "volume", "get",
        "lada-videos",
        remote_path,
        str(local_path),
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
        # 当作文件名处理
        local_dir = sys.argv[2] if len(sys.argv) > 2 else "."
        download_file(action, local_dir)


if __name__ == "__main__":
    main()
