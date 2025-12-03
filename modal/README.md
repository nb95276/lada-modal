# Modal Lada 视频修复

使用 Modal serverless GPU 运行 Lada 视频修复，功能与 Colab 版本一致。

## 功能

- ✅ URL 直接下载处理（支持 Alist/小雅）
- ✅ 批量处理（自动跳过已处理）
- ✅ 视频切割（长视频切成小段）
- ✅ 分段合并（处理完后合并）
- ✅ 模型选择（fast/accurate）
- ✅ 编码器选择（libx264/libx265）

## 快速开始

```bash
# 1. 安装 Modal
pip install modal
modal token new

# 2. 从小雅直链处理视频
modal run lada_modal.py --url "http://xiaoya.952786.xyz:5678/d/🏷️我的115/video.mp4"
```

## 常用命令

### 单视频处理

```bash
# 从 URL 下载并处理
modal run lada_modal.py --url "http://xiaoya.xxx/d/path/video.mp4"

# 处理 Volume 中的视频
modal run lada_modal.py --filename video.mp4

# 使用 accurate 模型（更准但慢）
modal run lada_modal.py --filename video.mp4 --detection accurate
```

### 批量处理

```bash
# 处理所有视频（自动跳过已处理）
modal run lada_modal.py --action batch

# 只处理分段文件
modal run lada_modal.py --action batch --pattern "_part"
```

### 长视频切割

```bash
# 切成 10 分钟一段
modal run lada_modal.py --action split --filename long_video.mp4 --segment 10

# 批量处理分段
modal run lada_modal.py --action batch --pattern "_part"

# 合并处理后的分段
modal run lada_modal.py --action merge --prefix "long_video_part" --output "final.mp4"
```

### 文件管理

```bash
# 列出输入文件
modal run lada_modal.py --action list-input

# 列出输出文件
modal run lada_modal.py --action list-output

# 上传视频到 Volume
python upload.py video.mp4

# 下载处理结果
python download.py all
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --detection | fast | 检测模型：fast（快）/ accurate（准） |
| --codec | libx264 | 编码器：libx264 / libx265 |
| --crf | 20 | 质量参数，越小越好（15-35） |
| --segment | 10 | 切割时每段时长（分钟） |

## GPU 选择

默认使用 T4（$0.16/h），如需更快可修改 `lada_modal.py` 中的 `gpu="T4"` 为：

- `gpu="A10G"` - $0.36/h，约快 2 倍
- `gpu="A100"` - $1.10/h，约快 4 倍

## 费用估算

Modal 每月 $30 免费额度：

| GPU | 价格 | 1小时视频耗时 | 费用 |
|-----|------|-------------|------|
| T4 | $0.16/h | ~2h | ~$0.32 |
| A10G | $0.36/h | ~50min | ~$0.30 |

## 完整工作流示例

```bash
# 1. 从小雅下载长视频
modal run lada_modal.py --url "http://xiaoya.xxx/d/path/movie.mp4"

# 如果视频很长，先切割
modal run lada_modal.py --action split --filename movie.mp4 --segment 15

# 2. 批量处理所有分段
modal run lada_modal.py --action batch --pattern "_part" --detection accurate

# 3. 合并处理后的分段
modal run lada_modal.py --action merge --prefix "movie_part" --output "movie_restored.mp4"

# 4. 下载结果
python download.py movie_restored.mp4
```
