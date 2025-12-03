# Modal + Lada 部署经验教训

## 成功配置

### Python 版本
- **必须使用 Python 3.12+**，Lada 的 `pyproject.toml` 明确要求 `requires-python = ">=3.12.0"`
- 不要用 3.11，会安装失败

### CLI vs GUI
- Lada 有两个入口点：
  - `lada` - GUI 版本，需要 PyGObject/GTK 依赖
  - `lada-cli` - CLI 版本，**无需 GUI 依赖**
- Modal 是无头环境，**必须用 `lada-cli`**
- GUI 依赖 (`pycairo`, `PyGObject`) 是可选的：`gui = ["pycairo", "PyGObject"]`

### 模型文件
- Lada 不会自动下载模型，需要手动预下载
- 模型必须放在运行目录的 `model_weights/` 下，或用完整路径指定
- 必需的模型文件：
  ```
  model_weights/
  ├── lada_mosaic_detection_model_v3.1_fast.pt      # 快速检测
  ├── lada_mosaic_detection_model_v3.1_accurate.pt  # 精确检测
  ├── lada_mosaic_restoration_model_generic_v1.2.pth # 修复模型
  └── 3rd_party/
      └── RealESRGAN_x4plus.pth                     # 超分辨率（可选）
  ```

### 命令行参数
- 参数名必须完整，不能缩写：
  - ❌ `--mosaic-detection` → 歧义错误
  - ✅ `--mosaic-detection-model-path`
  - ✅ `--mosaic-restoration-model-path`

## 镜像配置最佳实践

```python
image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "git", "wget")
    .pip_install("torch", "torchvision", ...)
    .run_commands(
        "pip install git+https://github.com/ladaapp/lada.git",
        # 模型下载到绝对路径
        "mkdir -p /root/model_weights/3rd_party",
        "wget -q -O /root/model_weights/xxx.pt https://...",
    )
    .workdir("/root")  # 设置工作目录
)
```

### 关键点
1. **先下载模型，再设置 workdir** - 或者用绝对路径
2. **workdir 必须是模型所在目录的父目录** - lada-cli 会在当前目录找 `model_weights/`
3. **用绝对路径更可靠** - 避免工作目录问题

## 踩过的坑

### 1. gi 模块问题
- **现象**：`ModuleNotFoundError: No module named 'gi'`
- **原因**：尝试安装 GUI 依赖，但 girepository 版本不兼容
- **解决**：不要装 GUI 依赖，直接用 `lada-cli`

### 2. 模型找不到
- **现象**：`FileNotFoundError: model_weights/xxx.pth can not be found`
- **原因**：模型下载到了构建时的目录，运行时工作目录不同
- **解决**：用绝对路径 `/root/model_weights/` 并设置 `workdir("/root")`

### 3. 参数歧义
- **现象**：`ambiguous option: --mosaic-restoration could match ...`
- **原因**：参数名缩写有多个匹配
- **解决**：使用完整参数名 `--mosaic-restoration-model-path`

## 编码器选择

| 编码器 | 类型 | 速度 | 适用场景 |
|--------|------|------|----------|
| h264_nvenc | GPU 硬编码 | 最快 | Modal T4 GPU |
| hevc_nvenc | GPU 硬编码 | 快 | 需要更好压缩 |
| libx264 | CPU 软编码 | 慢 | 无 GPU 环境 |
| libx265 | CPU 软编码 | 最慢 | 最佳压缩比 |

Modal 有 T4 GPU，默认用 `h264_nvenc`。

## 调试技巧

1. **先测试镜像构建**：`modal run xxx.py --action input`
2. **查看构建日志**：确认模型下载成功
3. **打印完整命令**：方便排查参数问题
4. **保留 stderr 输出**：错误信息在这里

## Modal Volume 下载

### 文件路径格式
- `modal volume ls` 返回的文件名带目录前缀：`output/filename.mp4`
- `modal volume get` 需要完整路径：`output/filename.mp4`
- 不要重复添加 `output/` 前缀

### 获取完整文件名
- 表格输出会截断长文件名（显示 `...`）
- 使用 `--json` 参数获取完整文件名：
  ```bash
  modal volume ls lada-videos /output --json
  ```

### 下载命令
```bash
# 正确
modal volume get lada-videos "output/video.mp4" "./video.mp4"

# 错误（路径重复）
modal volume get lada-videos "/output/output/video.mp4" ...
```

## 参考链接

- Lada GitHub: https://github.com/ladaapp/lada
- 模型下载: https://huggingface.co/ladaapp/lada
- Modal 文档: https://modal.com/docs
