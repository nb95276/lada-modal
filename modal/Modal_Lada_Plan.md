# Modal + Lada 视频修复方案

## 概述

使用 Modal 的 serverless GPU 运行 Lada 视频修复，利用每月 $30 免费额度。

## 架构

```
本地 → 上传视频到 Modal Volume → GPU 处理 → 下载结果
```

## 实现步骤

### 1. 环境准备
- 安装 Modal CLI: `pip install modal`
- 登录: `modal token new`
- 创建 Volume 存储视频文件

### 2. 创建 Modal App
- 定义 GPU 镜像（包含 Lada 依赖）
- 挂载 Volume 用于输入/输出
- 编写处理函数

### 3. 核心代码结构

```python
# lada_modal.py

import modal

# 定义镜像
image = modal.Image.debian_slim(python_version="3.12").pip_install(
    "lada @ git+https://github.com/ladaapp/lada.git"
)

# 创建 App
app = modal.App("lada-restore", image=image)

# 创建 Volume
volume = modal.Volume.from_name("lada-videos", create_if_missing=True)

@app.function(
    gpu="A10G",  # 或 "T4" 更便宜
    volumes={"/data": volume},
    timeout=3600,  # 1小时超时
)
def restore_video(input_filename: str):
    """处理单个视频"""
    import subprocess
    input_path = f"/data/input/{input_filename}"
    output_path = f"/data/output/restored_{input_filename}"
    
    subprocess.run([
        "lada-cli",
        "--input", input_path,
        "--output", output_path,
        "--codec", "libx264",
        "--crf", "20"
    ], check=True)
    
    return output_path

@app.local_entrypoint()
def main(filename: str):
    """本地入口"""
    result = restore_video.remote(filename)
    print(f"完成: {result}")
```

### 4. 使用流程

```bash
# 上传视频到 Volume
modal volume put lada-videos input/video.mp4 /input/

# 运行处理
modal run lada_modal.py --filename video.mp4

# 下载结果
modal volume get lada-videos /output/restored_video.mp4 ./
```

### 5. 可选优化

- **批量处理**: 用 `map` 并行处理多个视频
- **进度显示**: 用 `modal.interact()` 实时查看日志
- **自动切割**: 长视频先切割再并行处理
- **成本控制**: 用 T4 ($0.16/h) 代替 A10G ($0.36/h)

## 成本估算

| GPU | 价格 | 处理速度 | 1小时视频耗时 | 费用 |
|-----|------|---------|-------------|------|
| T4 | $0.16/h | ~5 fps | ~2h | ~$0.32 |
| A10G | $0.36/h | ~12 fps | ~50min | ~$0.30 |
| A100 | $1.10/h | ~25 fps | ~25min | ~$0.46 |

$30 免费额度大约能处理 50-100 小时视频（取决于 GPU 选择）。

## 文件结构

```
lada拉达/
├── modal/
│   ├── Modal_Lada_Plan.md  # 本文档
│   ├── README.md           # 使用说明
│   ├── lada_modal.py       # Modal 主程序 ✅
│   ├── upload.py           # 上传脚本 ✅
│   └── download.py         # 下载脚本 ✅
```

## 下一步

1. ~~注册 Modal 账号~~
2. ~~安装 CLI 并登录~~
3. ~~创建 lada_modal.py~~ ✅
4. 测试单个视频
5. 根据需要优化
