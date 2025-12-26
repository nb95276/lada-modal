# Modal 部署 Lada Docker 完成报告

## 完成内容

### 创建的文件

| 文件 | 说明 |
|-----|------|
| `lada_modal.py` | Modal 应用主代码 |
| `requirements.txt` | Modal 依赖 |
| `README.md` | 使用说明 |

### 关键技术点

1. **ENTRYPOINT 覆盖**：使用 `setup_dockerfile_commands=["ENTRYPOINT []"]` 清除默认入口点
2. **GPU 配置**：默认使用 T4 (~$0.59/h)
3. **Volume 存储**：使用 `lada-videos` Volume 持久化视频

---

## 使用方法

```bash
# 安装
pip install modal && modal setup

# 上传视频
modal volume put lada-videos /path/to/video.mp4 video.mp4

# 处理
modal run lada_modal.py --input-file video.mp4

# 下载结果
modal volume get lada-videos restored_video.mp4 ./
```

---

## 注意事项

- 需要 Modal 账户（支持 GitHub/Google 登录）
- GPU 按秒计费，处理完自动释放
- 首次运行会拉取 Docker 镜像（~2GB），后续有缓存
