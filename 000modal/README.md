# Lada Modal 部署

在 Modal 云平台上运行 [Lada](https://github.com/ladaapp/lada) 视频马赛克修复服务。

## 架构

```
GitHub Actions → Docker Hub → Modal
```

## 快速开始

### 1. 配置 GitHub Secrets

在 GitHub 仓库设置中添加：

| Secret | 说明 |
|--------|-----|
| `DOCKERHUB_USERNAME` | Docker Hub 用户名 |
| `DOCKERHUB_TOKEN` | Docker Hub Access Token |

### 2. 更新配置

编辑 `lada_modal.py`，替换 `YOUR_DOCKERHUB_USERNAME`：

```python
DOCKERHUB_USERNAME = "your_actual_username"
```

### 3. 推送代码

```bash
git add .
git commit -m "Add Lada Modal deployment"
git push
```

GitHub Actions 会自动构建并推送 Docker 镜像到 Docker Hub。

### 4. 运行 Modal

```bash
pip install modal
modal setup

# 上传视频
modal volume put lada-videos /path/to/video.mp4 video.mp4

# 处理视频
modal run lada_modal.py --input-file video.mp4

# 下载结果
modal volume get lada-videos restored_video.mp4 ./
```

## 文件说明

| 文件 | 说明 |
|-----|------|
| `Dockerfile` | 基于官方镜像，覆盖 ENTRYPOINT |
| `lada_modal.py` | Modal 应用代码 |
| `.github/workflows/docker.yml` | CI/CD 工作流 |
