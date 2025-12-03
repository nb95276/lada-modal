# -*- coding: utf-8 -*-
"""
Lada Video Restore on Modal
使用 Modal serverless GPU 运行 Lada 视频修复
功能：URL下载、视频切割、批量处理、分段合并、模型选择
"""

import modal

# 定义镜像 - 包含 Lada 及其依赖
# Lada requires Python >= 3.12, use lada-cli (no GUI/gi dependencies)
# Model weights are downloaded to /root/model_weights (lada-cli looks for relative path)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git", "wget")
    .pip_install(
        "torch",
        "torchvision",
        "opencv-python-headless",
        "numpy",
        "tqdm",
        "requests",
        "fastapi",  # Required for web endpoints
    )
    .run_commands(
        # Install Lada
        "pip install git+https://github.com/ladaapp/lada.git",
        # Download model weights to /root/model_weights (absolute path)
        "mkdir -p /root/model_weights/3rd_party",
        "wget -q -O /root/model_weights/lada_mosaic_detection_model_v3.1_fast.pt "
        "https://huggingface.co/ladaapp/lada/resolve/main/lada_mosaic_detection_model_v3.1_fast.pt",
        "wget -q -O /root/model_weights/lada_mosaic_detection_model_v3.1_accurate.pt "
        "https://huggingface.co/ladaapp/lada/resolve/main/lada_mosaic_detection_model_v3.1_accurate.pt",
        "wget -q -O /root/model_weights/lada_mosaic_restoration_model_generic_v1.2.pth "
        "https://huggingface.co/ladaapp/lada/resolve/main/lada_mosaic_restoration_model_generic_v1.2.pth",
        "wget -q -O /root/model_weights/3rd_party/RealESRGAN_x4plus.pth "
        "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    )
    .workdir("/root")  # lada-cli runs from here, finds model_weights/
)

# 创建 App
app = modal.App("lada-restore", image=image)

# 创建 Volume 用于存储视频
volume = modal.Volume.from_name("lada-videos", create_if_missing=True)

VOLUME_PATH = "/data"


@app.function(volumes={VOLUME_PATH: volume})
def list_files(subdir: str = ""):
    """列出 Volume 中的文件"""
    import os

    path = f"{VOLUME_PATH}/{subdir}" if subdir else VOLUME_PATH
    if not os.path.exists(path):
        return []

    files = []
    for item in sorted(os.listdir(path)):
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path):
            size_mb = os.path.getsize(item_path) / (1024 * 1024)
            files.append({"name": item, "size_mb": round(size_mb, 2)})
        else:
            files.append({"name": item + "/", "type": "dir"})
    return files


@app.function(volumes={VOLUME_PATH: volume}, timeout=3600)
def split_video(filename: str, segment_minutes: int = 10):
    """
    切割长视频为小段（防断联）

    Args:
        filename: 输入文件名
        segment_minutes: 每段时长（分钟）
    """
    import os
    import subprocess

    input_path = f"{VOLUME_PATH}/input/{filename}"
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    # 获取视频时长
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", input_path
        ],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip()) if result.returncode == 0 else 0
    duration_min = duration / 60

    print(f"Video: {filename}")
    print(f"Duration: {duration_min:.1f} min")
    print(f"Segment: {segment_minutes} min")

    if duration_min <= segment_minutes:
        print("Video is short, no need to split")
        return [filename]

    # 切割
    name, ext = os.path.splitext(filename)
    output_pattern = f"{VOLUME_PATH}/input/{name}_part%03d{ext}"

    cmd = [
        "ffmpeg", "-i", input_path,
        "-c", "copy", "-map", "0",
        "-segment_time", str(segment_minutes * 60),
        "-f", "segment", "-reset_timestamps", "1",
        output_pattern, "-y"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Split failed: {result.stderr}")

    # 列出分段
    input_dir = f"{VOLUME_PATH}/input"
    segments = sorted([f for f in os.listdir(input_dir) if f.startswith(f"{name}_part")])

    print(f"Created {len(segments)} segments")
    volume.commit()

    return segments


@app.function(volumes={VOLUME_PATH: volume}, timeout=1800)
def merge_videos(prefix: str, output_name: str = "merged.mp4"):
    """
    合并分段视频

    Args:
        prefix: 分段文件前缀（如 video_part）
        output_name: 输出文件名
    """
    import os
    import subprocess

    output_dir = f"{VOLUME_PATH}/output"
    os.makedirs(output_dir, exist_ok=True)

    # 找到所有分段（已处理的）
    files = sorted([f for f in os.listdir(output_dir) if prefix in f and f.endswith(".mp4")])

    if not files:
        raise FileNotFoundError(f"No files matching prefix: {prefix}")

    print(f"Found {len(files)} segments to merge")

    # 创建文件列表
    list_file = f"{VOLUME_PATH}/merge_list.txt"
    with open(list_file, "w") as f:
        for file in files:
            f.write(f"file '{output_dir}/{file}'\n")

    # 合并
    output_path = f"{output_dir}/{output_name}"
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", output_path, "-y"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Merge failed: {result.stderr}")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Merged: {output_name} ({size_mb:.1f} MB)")

    volume.commit()
    return output_name


@app.function(
    gpu="T4",
    volumes={VOLUME_PATH: volume},
    timeout=7200,
)
def restore_video(
    input_filename: str,
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "fast",
    skip_existing: bool = True,
):
    """
    处理单个视频

    Args:
        input_filename: 输入文件名
        codec: 编码器 (h264_nvenc/hevc_nvenc/libx264/libx265)
        crf: 质量参数 (越小越好，默认20)
        detection: 检测模型 (fast/accurate)
        skip_existing: 跳过已处理的文件
    """
    import os
    import subprocess

    input_path = f"{VOLUME_PATH}/input/{input_filename}"
    output_dir = f"{VOLUME_PATH}/output"
    os.makedirs(output_dir, exist_ok=True)

    name, ext = os.path.splitext(input_filename)
    output_filename = f"{name}_restored{ext}"
    output_path = f"{output_dir}/{output_filename}"

    # 跳过已处理
    if skip_existing and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Skip (exists): {output_filename} ({size_mb:.1f} MB)")
        return {"status": "skipped", "output": output_filename}

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input not found: {input_path}")

    print(f"Processing: {input_filename}")
    print(f"Detection: {detection}, Codec: {codec}, CRF: {crf}")

    # 构建命令 (使用 lada-cli，无需 GUI 依赖)
    # 模型路径在 /root/model_weights/
    model_dir = "/root/model_weights"
    cmd = [
        "lada-cli",
        "--input", input_path,
        "--output", output_path,
        "--codec", codec,
        "--crf", str(crf),
    ]

    # 检测模型选择 (需要完整路径和完整参数名)
    if detection == "accurate":
        cmd.extend(["--mosaic-detection-model-path", f"{model_dir}/lada_mosaic_detection_model_v3.1_accurate.pt"])
    else:
        cmd.extend(["--mosaic-detection-model-path", f"{model_dir}/lada_mosaic_detection_model_v3.1_fast.pt"])

    # 修复模型
    cmd.extend(["--mosaic-restoration-model-path", f"{model_dir}/lada_mosaic_restoration_model_generic_v1.2.pth"])

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"STDERR: {result.stderr}")
        raise RuntimeError(f"Lada failed: {result.stderr}")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done: {output_filename} ({size_mb:.1f} MB)")

    volume.commit()
    return {"status": "success", "output": output_filename}


@app.function(
    gpu="T4",
    volumes={VOLUME_PATH: volume},
    timeout=28800,  # 8小时
)
def restore_batch(
    pattern: str = "",
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "fast",
    skip_existing: bool = True,
):
    """
    批量处理视频

    Args:
        pattern: 文件名匹配模式（留空处理所有）
        codec: 编码器 (h264_nvenc/hevc_nvenc/libx264/libx265)
        crf: 质量参数
        detection: 检测模型
        skip_existing: 跳过已处理
    """
    import os
    import time

    input_dir = f"{VOLUME_PATH}/input"
    if not os.path.exists(input_dir):
        return {"error": "No input directory"}

    # 获取视频列表
    video_exts = (".mp4", ".mkv", ".avi", ".mov", ".webm")
    videos = sorted([
        f for f in os.listdir(input_dir)
        if f.lower().endswith(video_exts) and (not pattern or pattern in f)
    ])

    if not videos:
        return {"error": "No videos found"}

    print(f"Found {len(videos)} videos")
    print(f"Settings: detection={detection}, codec={codec}, crf={crf}")
    print("=" * 50)

    results = {"success": 0, "skipped": 0, "failed": 0, "details": []}
    start_time = time.time()

    for i, video in enumerate(videos):
        print(f"\n[{i+1}/{len(videos)}] {video}")

        try:
            result = restore_video.local(
                video, codec, crf, detection, skip_existing
            )
            if result["status"] == "skipped":
                results["skipped"] += 1
            else:
                results["success"] += 1
            results["details"].append({"file": video, **result})
        except Exception as e:
            print(f"Error: {e}")
            results["failed"] += 1
            results["details"].append({"file": video, "status": "failed", "error": str(e)})

    elapsed = time.time() - start_time
    results["elapsed_minutes"] = round(elapsed / 60, 1)

    print("\n" + "=" * 50)
    print(f"Batch complete: {results['success']} success, {results['skipped']} skipped, {results['failed']} failed")
    print(f"Time: {results['elapsed_minutes']} min")

    return results


@app.function(
    gpu="T4",
    volumes={VOLUME_PATH: volume},
    timeout=14400,
)
def restore_from_url(
    url: str,
    output_name: str = "",
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "fast",
):
    """
    从 URL 下载视频并修复（支持 Alist/小雅 直链）
    """
    import os
    import subprocess
    import urllib.parse

    import requests

    input_dir = f"{VOLUME_PATH}/input"
    output_dir = f"{VOLUME_PATH}/output"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 从 URL 提取文件名
    if not output_name:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        output_name = os.path.basename(path)
        if not output_name:
            output_name = "video.mp4"

    input_path = f"{input_dir}/{output_name}"

    # 下载视频
    print(f"Downloading: {url}")
    print(f"Save to: {input_path}")

    wget_cmd = ["wget", "-q", "--show-progress", "-O", input_path, url]
    result = subprocess.run(wget_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("wget failed, trying requests...")
        resp = requests.get(url, stream=True, timeout=600, allow_redirects=True)
        resp.raise_for_status()
        with open(input_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

    file_size = os.path.getsize(input_path) / (1024 * 1024)
    print(f"Downloaded: {file_size:.1f} MB")

    # 处理
    result = restore_video.local(output_name, codec, crf, detection, skip_existing=False)

    volume.commit()
    return result


@app.local_entrypoint()
def main(
    filename: str = "",
    url: str = "",
    action: str = "restore",
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "fast",
    pattern: str = "",
    segment: int = 10,
    prefix: str = "",
    output: str = "",
):
    """
    Lada Modal CLI

    Usage:
        # 处理单个视频
        modal run lada_modal.py --filename video.mp4

        # 从 URL 下载并处理
        modal run lada_modal.py --url "http://xiaoya.xxx/d/path/video.mp4"

        # 批量处理所有视频
        modal run lada_modal.py --action batch

        # 批量处理匹配的视频
        modal run lada_modal.py --action batch --pattern "_part"

        # 切割长视频
        modal run lada_modal.py --action split --filename video.mp4 --segment 10

        # 合并分段
        modal run lada_modal.py --action merge --prefix "video_part" --output "final.mp4"

        # 列出文件
        modal run lada_modal.py --action input
        modal run lada_modal.py --action output

    Options:
        --detection fast/accurate  检测模型（accurate更准但慢）
        --codec h264_nvenc/hevc_nvenc/libx264/libx265  编码器（默认nvenc硬编码）
        --crf 20                   质量（越小越好）
    """
    if action in ("list-input", "list_input", "input"):
        files = list_files.remote("input")
        print("Input files:")
        for i, f in enumerate(files, 1):
            if 'size_mb' in f:
                print(f"  [{i}] {f['name']} ({f['size_mb']} MB)")
            else:
                print(f"  [{i}] {f['name']}")

    elif action in ("list-output", "list_output", "output"):
        files = list_files.remote("output")
        print("Output files:")
        for i, f in enumerate(files, 1):
            if 'size_mb' in f:
                print(f"  [{i}] {f['name']} ({f['size_mb']} MB)")
            else:
                print(f"  [{i}] {f['name']}")

    elif action == "split":
        if not filename:
            print("Error: --filename required for split")
            return
        print(f"Splitting: {filename} into {segment} min segments")
        segments = split_video.remote(filename, segment)
        print(f"Created segments: {segments}")

    elif action == "merge":
        if not prefix:
            print("Error: --prefix required for merge")
            return
        output_name = output or "merged.mp4"
        print(f"Merging files with prefix: {prefix}")
        result = merge_videos.remote(prefix, output_name)
        print(f"Merged: {result}")

    elif action == "batch":
        print(f"Batch processing (pattern={pattern or 'all'})")
        result = restore_batch.remote(pattern, codec, crf, detection, skip_existing=True)
        print(f"Result: {result}")

    elif action == "restore":
        if url:
            print(f"Restore from URL: {url}")
            result = restore_from_url.remote(url, filename, codec, crf, detection)
            print(f"Result: {result}")
        elif filename:
            print(f"Restore: {filename}")
            result = restore_video.remote(filename, codec, crf, detection, skip_existing=False)
            print(f"Result: {result}")
        else:
            print("Error: --filename or --url required")

    else:
        print(f"Unknown action: {action}")
        print("Available: restore, batch, split, merge, input, output")


# ============================================================
# Web API 端点
# 部署: modal deploy lada_modal.py
# ============================================================

@app.function(
    gpu="T4",
    volumes={VOLUME_PATH: volume},
    timeout=14400,
)
@modal.fastapi_endpoint(method="POST")
def api_restore(
    url: str,
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "fast",
):
    """
    Web API: 从 URL 下载视频并修复

    POST /api_restore
    Body: {"url": "http://...", "codec": "h264_nvenc", "crf": 20, "detection": "fast"}

    Returns: {"status": "success", "output": "filename.mp4", "message": "..."}
    """
    import os
    import subprocess
    import urllib.parse

    import requests as req

    input_dir = f"{VOLUME_PATH}/input"
    output_dir = f"{VOLUME_PATH}/output"
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 从 URL 提取文件名
    parsed = urllib.parse.urlparse(url)
    path = urllib.parse.unquote(parsed.path)
    filename = os.path.basename(path) or "video.mp4"
    input_path = f"{input_dir}/{filename}"

    # 下载视频
    try:
        wget_cmd = ["wget", "-q", "-O", input_path, url]
        result = subprocess.run(wget_cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            resp = req.get(url, stream=True, timeout=600, allow_redirects=True)
            resp.raise_for_status()
            with open(input_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
    except Exception as e:
        return {"status": "error", "message": f"Download failed: {e}"}

    file_size = os.path.getsize(input_path) / (1024 * 1024)

    # 处理视频
    name, ext = os.path.splitext(filename)
    output_filename = f"{name}_restored{ext}"
    output_path = f"{output_dir}/{output_filename}"

    model_dir = "/root/model_weights"
    cmd = [
        "lada-cli",
        "--input", input_path,
        "--output", output_path,
        "--codec", codec,
        "--crf", str(crf),
    ]

    if detection == "accurate":
        cmd.extend(["--mosaic-detection-model-path", f"{model_dir}/lada_mosaic_detection_model_v3.1_accurate.pt"])
    else:
        cmd.extend(["--mosaic-detection-model-path", f"{model_dir}/lada_mosaic_detection_model_v3.1_fast.pt"])

    cmd.extend(["--mosaic-restoration-model-path", f"{model_dir}/lada_mosaic_restoration_model_generic_v1.2.pth"])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return {"status": "error", "message": f"Processing failed: {result.stderr[:500]}"}

    output_size = os.path.getsize(output_path) / (1024 * 1024)
    volume.commit()

    return {
        "status": "success",
        "output": output_filename,
        "input_size_mb": round(file_size, 2),
        "output_size_mb": round(output_size, 2),
        "message": f"Video restored. Use 'modal volume get lada-videos output/{output_filename}' to download.",
    }


@app.function(volumes={VOLUME_PATH: volume})
@modal.fastapi_endpoint(method="GET")
def api_list_output():
    """
    Web API: 列出已完成的视频

    GET /api_list_output
    Returns: {"files": [{"name": "...", "size_mb": ...}, ...]}
    """
    import os

    output_dir = f"{VOLUME_PATH}/output"
    if not os.path.exists(output_dir):
        return {"files": []}

    files = []
    for item in sorted(os.listdir(output_dir)):
        item_path = os.path.join(output_dir, item)
        if os.path.isfile(item_path):
            size_mb = os.path.getsize(item_path) / (1024 * 1024)
            files.append({"name": item, "size_mb": round(size_mb, 2)})

    return {"files": files}
