"""
Lada 视频马赛克修复服务 - Modal 部署
https://github.com/ladaapp/lada
"""
import modal
import subprocess

app = modal.App("lada-video-processor")

# 从 Docker Hub 导入自定义 Lada 镜像
DOCKERHUB_USERNAME = "fkccp"

lada_image = modal.Image.from_registry(
    f"{DOCKERHUB_USERNAME}/lada_modal:latest"
)

# 持久化存储卷
volume = modal.Volume.from_name("lada-videos", create_if_missing=True)


@app.function(
    image=lada_image,
    gpu="T4",  # 可选: T4, L4, A10, A100
    volumes={"/data": volume},
    timeout=3600,  # 1小时超时
)
def process_video(
    input_filename: str,
    output_filename: str = None,
    model: str = "generic",  # generic 或 fast
) -> dict:
    """
    处理视频文件，修复马赛克区域
    
    Args:
        input_filename: 输入视频文件名（需先上传到 volume）
        output_filename: 输出视频文件名（可选）
        model: 使用的模型 - "generic" (更好质量) 或 "fast" (更快速度)
    
    Returns:
        处理结果字典，包含状态和输出文件名
    """
    input_path = f"/data/{input_filename}"
    if output_filename is None:
        output_filename = f"restored_{input_filename}"
    output_path = f"/data/{output_filename}"
    
    # 构建命令
    cmd = ["lada-cli", "--input", input_path, "--output", output_path]
    if model == "fast":
        cmd.extend(["--detection-model", "fast"])
    
    print(f"执行命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        volume.commit()  # 持久化输出文件
        return {
            "success": True,
            "output": output_filename,
            "message": "视频处理完成"
        }
    else:
        return {
            "success": False,
            "error": result.stderr,
            "message": "处理失败"
        }


@app.function(image=lada_image, volumes={"/data": volume})
def list_files() -> list:
    """列出 volume 中的文件"""
    import os
    files = os.listdir("/data")
    return files


@app.local_entrypoint()
def main(input_file: str, model: str = "generic"):
    """
    本地入口点
    
    用法:
        modal run lada_modal.py --input-file video.mp4
        modal run lada_modal.py --input-file video.mp4 --model fast
    """
    print(f"开始处理: {input_file}")
    result = process_video.remote(input_file, model=model)
    print(f"结果: {result}")
