# -*- coding: utf-8 -*-
"""Lada Video Restore on Modal v7 DEV - Docker Based"""

import modal

image = (
    modal.Image.from_registry("fkccp/lada-modal:latest")
    .pip_install("fastapi[standard]", "requests", "tqdm")
)

app = modal.App("lada-restore-v7-dev", image=image)
volume = modal.Volume.from_name("lada-videos", create_if_missing=True)
VOLUME_PATH = "/data"
MODEL_DIR = "/model_weights"



@app.function(volumes={VOLUME_PATH: volume})
def list_files(subdir: str = ""):
    """List files in Volume"""
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
    """Split long video into segments, reuse existing if available"""
    import os
    import subprocess

    input_path = f"{VOLUME_PATH}/input/{filename}"
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"File not found: {input_path}")

    name, ext = os.path.splitext(filename)
    input_dir = f"{VOLUME_PATH}/input"
    
    existing_segments = sorted([f for f in os.listdir(input_dir) if f.startswith(f"{name}_part") and f.endswith(ext)])
    if existing_segments:
        print(f"Found {len(existing_segments)} existing segments, reusing")
        return existing_segments

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", input_path],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"ffprobe failed: {result.stderr or 'no output'}")
    duration = float(result.stdout.strip())
    duration_min = duration / 60

    print(f"Video: {filename}, Duration: {duration_min:.1f} min")

    if duration_min <= segment_minutes:
        print("Video is short, no need to split")
        return [filename]

    output_pattern = f"{input_dir}/{name}_part%03d{ext}"

    cmd = ["ffmpeg", "-i", input_path, "-c", "copy", "-map", "0",
           "-segment_time", str(segment_minutes * 60),
           "-f", "segment", "-reset_timestamps", "1", output_pattern, "-y"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Split failed: {result.stderr}")

    segments = sorted([f for f in os.listdir(input_dir) if f.startswith(f"{name}_part")])
    print(f"Created {len(segments)} segments")
    volume.commit()
    return segments


@app.function(volumes={VOLUME_PATH: volume}, timeout=1800)
def merge_videos(prefix: str, output_name: str = "merged.mp4"):
    """Merge video segments"""
    import os
    import subprocess

    volume.reload()

    output_dir = f"{VOLUME_PATH}/output"
    os.makedirs(output_dir, exist_ok=True)

    all_files = os.listdir(output_dir)
    print(f"All files in output: {all_files}")

    files = sorted([f for f in all_files if prefix in f and f.endswith(".mp4")])
    if not files:
        raise FileNotFoundError(f"No files matching prefix: {prefix}")

    print(f"Found {len(files)} segments to merge")

    list_file = f"{VOLUME_PATH}/merge_list.txt"
    with open(list_file, "w") as f:
        for file in files:
            f.write(f"file '{output_dir}/{file}'\n")

    output_path = f"{output_dir}/{output_name}"
    cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", output_path, "-y"]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Merge failed: {result.stderr}")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Merged: {output_name} ({size_mb:.1f} MB)")
    volume.commit()
    return output_name


@app.function(gpu="T4", volumes={VOLUME_PATH: volume}, timeout=7200)
def restore_video(
    input_filename: str,
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "v4-fast",
    max_clip_length: int = 900,
    skip_existing: bool = True,
):
    """Process single video
    
    Args:
        input_filename: Video file name in input directory
        codec: FFmpeg codec (h264_nvenc for GPU, libx264 for CPU)
        crf: Quality (18-20 recommended, lower = better quality)
        detection: Detection model (v4-fast default, v4-accurate/v2/fast/accurate available)
        max_clip_length: Max frames per clip (900 = more stable, 180 = less memory)
        skip_existing: Skip if output already exists
    """
    import os
    import subprocess

    input_path = f"{VOLUME_PATH}/input/{input_filename}"
    output_dir = f"{VOLUME_PATH}/output"
    os.makedirs(output_dir, exist_ok=True)

    name, ext = os.path.splitext(input_filename)
    output_filename = f"{name}_restored_{detection}{ext}"
    output_path = f"{output_dir}/{output_filename}"

    if skip_existing and os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"Skip (exists): {output_filename} ({size_mb:.1f} MB)")
        return {"status": "skipped", "output": output_filename, "file": input_filename}

    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input not found: {input_path}")

    print(f"Processing: {input_filename}")
    print(f"Detection: {detection}, Codec: {codec}, CRF: {crf}, MaxClip: {max_clip_length}")

    model_dir = MODEL_DIR
    detection_models = {
        "v4-fast": "lada_mosaic_detection_model_v4_fast.pt",
        "v4-accurate": "lada_mosaic_detection_model_v4_accurate.pt",
        "fast": "lada_mosaic_detection_model_v3.1_fast.pt",
        "accurate": "lada_mosaic_detection_model_v3.1_accurate.pt",
        "v2": "lada_mosaic_detection_model_v2.pt",
    }
    detection_model = detection_models.get(detection, detection_models["v4-fast"])

    cmd = [
        "lada-cli",
        "--input", input_path,
        "--output", output_path,
        "--encoder", codec,
        "--encoder-options", f"-crf {crf}",
        "--max-clip-length", str(max_clip_length),
        "--mosaic-detection-model", f"{model_dir}/{detection_model}",
        "--mosaic-restoration-model", f"{model_dir}/lada_mosaic_restoration_model_generic_v1.2.pth",
    ]

    print(f"Running: {' '.join(cmd)}")
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    ) as process:
        output_lines = []
        last_reported = 0

        for line in process.stdout:
            output_lines.append(line)
            if "Processing video:" in line:
                try:
                    pct = int(line.split("%")[0].split()[-1])
                    milestone = (pct // 25) * 25
                    if milestone > last_reported:
                        last_reported = milestone
                        print(f"  {input_filename}: {pct}%", flush=True)
                except (ValueError, IndexError):
                    pass
            elif "error" in line.lower() or "failed" in line.lower():
                print(line.strip(), flush=True)

        process.wait()

        if process.returncode != 0:
            print(f"Lada failed with return code: {process.returncode}")
            raise RuntimeError(f"Lada failed: {''.join(output_lines[-20:])}")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done: {output_filename} ({size_mb:.1f} MB)")
    volume.commit()
    return {"status": "success", "output": output_filename, "file": input_filename}


@app.function(volumes={VOLUME_PATH: volume}, timeout=3600)
def parallel_restore(
    filename: str,
    segment_minutes: int = 10,
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "v4-fast",
    max_clip_length: int = 900,
    max_parallel: int = 10,
):
    """Parallel processing: split -> parallel restore -> merge"""
    import os
    import time
    from tqdm import tqdm

    start_time = time.time()
    name, ext = os.path.splitext(filename)
    
    print("=" * 50)
    print(f"PARALLEL RESTORE: {filename}")
    print(f"Segment: {segment_minutes} min, Max parallel: {max_parallel}")
    print("=" * 50)

    print("\n[1/3] Splitting video...")
    segments = split_video.local(filename, segment_minutes)
    
    if len(segments) == 1 and segments[0] == filename:
        print("Video is short, processing directly...")
        result = restore_video.remote(filename, codec, crf, detection, max_clip_length, skip_existing=False)
        return {
            "status": "success",
            "mode": "direct",
            "output": result["output"],
            "elapsed_minutes": round((time.time() - start_time) / 60, 1),
        }

    print(f"Split into {len(segments)} segments")

    print(f"\n[2/3] Processing {len(segments)} segments in parallel...")
    
    volume.reload()
    output_dir = f"{VOLUME_PATH}/output"
    existing_files = set(os.listdir(output_dir)) if os.path.exists(output_dir) else set()
    
    pending_segments = []
    for seg in segments:
        seg_name, seg_ext = os.path.splitext(seg)
        expected_output = f"{seg_name}_restored_{detection}{seg_ext}"
        if expected_output in existing_files:
            print(f"  Skip (exists): {seg}")
        else:
            pending_segments.append(seg)
    
    if not pending_segments:
        print("All segments already processed!")
    else:
        print(f"Pending: {len(pending_segments)}/{len(segments)} segments")
        print(f"Starting up to {min(len(pending_segments), max_parallel)} GPU instances...")
    
    results = []
    success_count = len(segments) - len(pending_segments)
    failed_count = 0

    if pending_segments:
        with tqdm(total=len(pending_segments), desc="GPU Processing", unit="seg", ncols=80) as pbar:
            for result in restore_video.starmap(
                [(seg, codec, crf, detection, max_clip_length, True) for seg in pending_segments]
            ):
                results.append(result)
                pbar.update(1)
                if result.get("status") in ("success", "skipped"):
                    success_count += 1
                    pbar.set_postfix_str(f"{result.get('file', '')[:25]}")
                else:
                    failed_count += 1
                    pbar.set_postfix_str(f"FAIL:{result.get('file', '')[:20]}")
    
    if failed_count > 0:
        return {
            "status": "partial",
            "success": success_count,
            "failed": failed_count,
            "results": results,
            "elapsed_minutes": round((time.time() - start_time) / 60, 1),
        }

    print(f"\n[3/3] Merging {len(segments)} segments...")
    
    restored_prefix = f"{name}_part"
    output_name = f"{name}_restored_{detection}{ext}"
    
    merged = merge_videos.local(restored_prefix, output_name)
    
    elapsed = round((time.time() - start_time) / 60, 1)
    print("\n" + "=" * 50)
    print(f"COMPLETE: {output_name}")
    print(f"Segments: {len(segments)}, Time: {elapsed} min")
    print("=" * 50)
    
    return {
        "status": "success",
        "mode": "parallel",
        "segments": len(segments),
        "output": merged,
        "elapsed_minutes": elapsed,
    }


def download_with_progress(url: str, output_path: str) -> int:
    """Download file with aria2c (multi-threaded) or fallback to requests"""
    import os
    import subprocess
    import shutil
    
    print(f"Downloading: {url[:100]}...")
    
    # 检测是否是 115 网盘链接（限制并发连接数）
    is_115 = any(x in url.lower() for x in ['115cdn', '115.com', 'xiaoya', '952786'])
    connections = "3" if is_115 else "16"
    
    if shutil.which("aria2c"):
        output_dir = os.path.dirname(output_path)
        output_name = os.path.basename(output_path)
        cmd = [
            "aria2c",
            "-x", connections,
            "-s", connections,
            "-k", "1M",
            "-d", output_dir,
            "-o", output_name,
            "--file-allocation=none",
            "--console-log-level=notice",
            "--max-tries=3",
            "--retry-wait=5",
            url
        ]
        print(f"Using aria2c with {connections} connection(s)..." + (" (115 detected)" if is_115 else ""))
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode == 0 and os.path.exists(output_path):
            return os.path.getsize(output_path)
        # 清理可能的部分下载文件
        if os.path.exists(output_path):
            os.remove(output_path)
        aria_file = output_path + ".aria2"
        if os.path.exists(aria_file):
            os.remove(aria_file)
        print("aria2c failed, falling back to requests...")
    
    import requests
    from tqdm import tqdm
    
    resp = requests.get(url, stream=True, timeout=600, allow_redirects=True)
    resp.raise_for_status()
    
    total_size = int(resp.headers.get('content-length', 0))
    
    with open(output_path, 'wb') as f:
        if total_size > 0:
            with tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc="Download",
                ncols=80,
            ) as pbar:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        else:
            downloaded = 0
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded % (10 * 1024 * 1024) == 0:
                        print(f"  Downloaded: {downloaded / (1024*1024):.1f} MB")
    
    return os.path.getsize(output_path)


@app.function(gpu="T4", volumes={VOLUME_PATH: volume}, timeout=14400)
def restore_from_url(
    url: str,
    output_name: str = "",
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "v4-fast",
    max_clip_length: int = 900,
    parallel: bool = False,
    segment_minutes: int = 10,
):
    """Download video from URL and restore"""
    import os
    import urllib.parse

    input_dir = f"{VOLUME_PATH}/input"
    os.makedirs(input_dir, exist_ok=True)

    if not output_name:
        parsed = urllib.parse.urlparse(url)
        path = urllib.parse.unquote(parsed.path)
        output_name = os.path.basename(path) or "video.mp4"

    input_path = f"{input_dir}/{output_name}"

    file_size = download_with_progress(url, input_path)
    print(f"Downloaded: {file_size / (1024*1024):.1f} MB")
    volume.commit()

    if parallel:
        result = parallel_restore.remote(output_name, segment_minutes, codec, crf, detection, max_clip_length)
    else:
        result = restore_video.local(output_name, codec, crf, detection, max_clip_length, skip_existing=False)
    
    return result


@app.function(volumes={VOLUME_PATH: volume}, timeout=3600)
@modal.fastapi_endpoint(method="GET")
def download_file(filename: str = ""):
    """Web endpoint to download files from volume"""
    import os
    from fastapi.responses import FileResponse, JSONResponse
    
    if not filename:
        output_dir = f"{VOLUME_PATH}/output"
        if os.path.exists(output_dir):
            files = sorted(os.listdir(output_dir))
            return JSONResponse({"files": files})
        return JSONResponse({"files": []})
    
    if not filename.startswith("output/"):
        filename = f"output/{filename}"
    
    file_path = f"{VOLUME_PATH}/{filename}"
    if not os.path.exists(file_path):
        return JSONResponse({"error": f"File not found: {filename}"}, status_code=404)
    
    return FileResponse(
        file_path,
        filename=os.path.basename(file_path),
        media_type="video/mp4"
    )


@app.local_entrypoint()
def main(
    filename: str = "",
    url: str = "",
    action: str = "restore",
    codec: str = "h264_nvenc",
    crf: int = 20,
    detection: str = "v4-fast",
    max_clip: int = 900,
    pattern: str = "",
    segment: int = 10,
    prefix: str = "",
    output: str = "",
    parallel: bool = False,
    max_parallel: int = 10,
):
    """
    Lada Modal CLI v7 DEV - Docker Based with v4 Models
    
    Default: detection=v4-fast, max_clip=900
    
    Examples:
        modal run lada_modal_v7_dev.py --url "http://..." --parallel
        modal run lada_modal_v7_dev.py --action parallel --filename video.mp4
        modal run lada_modal_v7_dev.py --filename video.mp4 --detection v4-accurate
    """
    import time
    import re
    start = time.time()
    
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
            print("Error: --filename required")
            return
        segments = split_video.remote(filename, segment)
        print(f"Segments: {segments}")

    elif action == "merge":
        def get_mergeable_prefixes():
            files = list_files.remote("output")
            prefixes = {}
            for f in files:
                name = f.get('name', '')
                match = re.match(r'(.+_part)\d+.*\.mp4$', name)
                if match:
                    p = match.group(1)
                    if p not in prefixes:
                        prefixes[p] = []
                    prefixes[p].append(name)
            return prefixes

        if not prefix:
            prefixes = get_mergeable_prefixes()
            if not prefixes:
                print("No mergeable segments found in output")
                return

            print("Mergeable groups:")
            prefix_list = list(prefixes.keys())
            for i, p in enumerate(prefix_list, 1):
                count = len(prefixes[p])
                print(f"  [{i}] {p}* ({count} segments)")
            return

        if prefix.isdigit():
            prefixes = get_mergeable_prefixes()
            prefix_list = list(prefixes.keys())
            idx = int(prefix) - 1
            if 0 <= idx < len(prefix_list):
                prefix = prefix_list[idx]
                print(f"Selected prefix: {prefix}")
            else:
                print(f"Error: Invalid index {prefix}")
                return

        result = merge_videos.remote(prefix, output or "merged.mp4")
        print(f"Merged: {result}")

    elif action == "parallel":
        if not filename:
            print("Error: --filename required")
            return
        if filename.isdigit():
            files = list_files.remote("input")
            idx = int(filename) - 1
            if 0 <= idx < len(files):
                filename = files[idx]['name']
                print(f"Selected: {filename}")
            else:
                print(f"Error: Invalid index {filename}")
                return
        print(f"Starting parallel restore: {filename}")
        print(f"Segment: {segment} min, Max parallel: {max_parallel}, MaxClip: {max_clip}")
        result = parallel_restore.remote(filename, segment, codec, crf, detection, max_clip, max_parallel)
        print(f"\nResult: {result}")

    elif action == "restore":
        if url:
            result = restore_from_url.remote(url, filename, codec, crf, detection, max_clip, parallel, segment)
        elif filename:
            if filename.isdigit():
                files = list_files.remote("input")
                idx = int(filename) - 1
                if 0 <= idx < len(files):
                    filename = files[idx]['name']
                    print(f"Selected: {filename}")
                else:
                    print(f"Error: Invalid index {filename}")
                    return
            if parallel:
                result = parallel_restore.remote(filename, segment, codec, crf, detection, max_clip, max_parallel)
            else:
                result = restore_video.remote(filename, codec, crf, detection, max_clip, skip_existing=False)
        else:
            print("Error: --filename or --url required")
            return
        print(f"\nResult: {result}")

    else:
        print(f"Unknown action: {action}")
        print("Available actions:")
        print("  restore   - Process single video (add --parallel for parallel mode)")
        print("  parallel  - Split + parallel process + merge")
        print("  split     - Split video into segments")
        print("  merge     - Merge segments")
        print("  input     - List input files")
        print("  output    - List output files")
        return
    
    elapsed = round((time.time() - start) / 60, 1)
    print(f"\nTotal time: {elapsed} min")
