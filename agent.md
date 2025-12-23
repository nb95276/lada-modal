 请始终使用简体中文与我交流。

## 核心开发指南

### 1. 环境管理 (Windows)
- **虚拟环境 (Venv)**: 在创建 `.bat` 或 `.ps1` 启动脚本时，必须显式激活 `.venv`。
  - `.bat` 示例: `if exist ".venv\Scripts\activate.bat" call .venv\Scripts\activate.bat`
  - 避免依赖系统 Python，防止 3.14+ 等不兼容版本导致的崩溃。

### 2. 字符编码
- **中文兼容性**: 
  - `.bat` 必须包含 `chcp 65001 > nul`。
  - `.ps1` 必须设置 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`。
  - 文件保存应使用 `UTF-8` 编码，且写入时避免使用不稳定的 `Out-File`。

### 3. CI/CD 最佳实践
- **Docker 构建**: 
  - 尽可能使用自定义 Docker Hub 镜像以减少 Modal 启动时的冷启动时间 (安装依赖/模型下载)。
  - GitHub Actions 必须监听特定文件路径 (如 `Dockerfile`) 以精准触发构建。

### 4. 任务自主性
- **高并发处理**: 在并行处理大量视频时，必须提供可视化进度条 (`tqdm`)。
- **路径寻址**: 始终使用相对脚本位置的绝对路径 (`%~dp0` 或 `$PSScriptRoot`)。
