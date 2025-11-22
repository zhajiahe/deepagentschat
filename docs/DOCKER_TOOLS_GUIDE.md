# Docker 共享容器工具系统指南

## 1. 简介

本项目采用创新的**共享容器+目录隔离**架构，为每个用户提供独立、安全且高性能的代码执行环境。相比于传统的"每个会话一个容器"方案，该架构在保持足够隔离性的同时，极大地降低了资源消耗和启动延迟。

## 2. 核心特性

- **🚀 高性能**: 所有用户共享一个长期运行的容器，无需为每个请求启动新容器，毫秒级响应。
- **🛡️ 资源隔离**: 每个用户拥有独立的工作目录 (`/workspace/{user_id}`)，互不干扰。
- **🎭 路径隐藏**: 系统自动过滤绝对路径，Agent 对真实物理路径无感，统一视为当前目录 (`.`)，增强安全性和 Agent 稳定性。
- **⚡ 极速构建**: 采用 `uv` 包管理器和国内镜像源（阿里云/DaoCloud），构建速度提升 10 倍以上。
- **🔄 双模式兼容**: 支持本地执行（开发调试用）和 Docker 执行（生产部署用）无缝切换。

## 3. 快速开始

### 3.1 环境准备
确保已安装 Docker 和 Docker Compose。

### 3.2 构建工具镜像
我们提供了针对国内网络优化的构建脚本，内置了阿里云源和 `uv` 加速：

```bash
bash docker/build-tools.sh --cn
```

### 3.3 启动服务
使用 Docker Compose 一键启动主程序和工具容器：

```bash
docker compose up -d --build
```

这将启动：
1. **deepagentschat-app**: 主应用程序
2. **deepagentschat-tools**: 共享工具容器

## 4. 配置说明 (.env)

在 `.env` 文件中配置以下参数以启用 Docker 模式：

```ini
# 启用 Docker 工具模式
USE_DOCKER_TOOLS=true

# Docker 镜像配置
DOCKER_IMAGE=deepagentschat-tools:latest
DOCKER_CPU_LIMIT=2.0
DOCKER_MEMORY_LIMIT=1g
DOCKER_NETWORK_MODE=none  # 建议设为 none 以禁止网络访问
DOCKER_TIMEOUT=30
```

## 5. 架构设计细节

### 5.1 工作流
1. **文件上传**: 用户上传文件 -> API 将其存入 `/workspace/{user_id}/` -> 返回文件名（相对路径）。
2. **命令执行**: Agent 发送命令 -> `SharedContainerManager` 接收 -> 在容器内 `/workspace/{user_id}` 目录下以 `tooluser` 身份执行。
3. **结果处理**: 捕获 stdout/stderr -> **自动替换绝对路径为 `.`** -> 返回给 Agent。

### 5.2 安全机制
- **非 Root 运行**: 容器内所有操作均以 `tooluser` (uid 1000) 身份执行。
- **Capability Drop**: 容器启动时移除了所有特权 Capabilities (`cap_drop=["ALL"]`)。
- **初始化脚本**: 每次执行命令前，系统会检查用户目录和 `.tools` 工具集是否就绪，并自动修正权限。
- **路径隐藏**: Agent 无法探知自己的真实绝对路径，防止越权访问尝试。

### 5.3 工具自动注入
镜像构建时已包含标准数据分析工具（在 `/opt/tools`）。当用户首次使用时，系统会自动将其复制到用户的 `.tools` 目录，确保每个用户都有完整的工具集。

## 6. 常见问题 (FAQ)

### Q: 为什么我上传了文件，Agent 却找不到？
A: 请确保 Agent 没有使用绝对路径。系统已配置为对 Agent 隐藏绝对路径。如果 Agent 尝试访问 `/workspace/...`，可能会因为路径被替换或权限问题而失败。Agent 应该始终操作当前目录。

### Q: 如何重置环境？
A: 您可以删除工具容器和 Volume 来重置所有用户数据：
```bash
docker rm -f deepagentschat-shared-tools
docker volume rm deepagentschat-workspace
```

### Q: 构建镜像太慢怎么办？
A: 请务必使用 `--cn` 参数构建，它使用了国内镜像源和 `uv` 加速：
```bash
bash docker/build-tools.sh --cn
```
