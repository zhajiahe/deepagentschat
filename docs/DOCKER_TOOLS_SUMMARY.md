# Docker 工具系统总结

## 📦 新增文件概览

### 核心实现

1. **app/core/shared_container.py** - 共享容器管理器
   - 管理一个长期运行的 Docker 容器
   - 所有用户共享，通过目录隔离
   - 提供文件操作和命令执行接口

2. **app/core/storage.py** - 统一存储配置
   - 统一管理存储路径
   - 提供路径安全验证
   - 供多个模块共享使用

3. **app/tools_docker.py** - Docker 版工具实现
   - shell_exec: 在共享容器中执行命令
   - write_file: 写入文件到容器
   - read_file: 从容器读取文件

### Docker 配置

4. **docker/Dockerfile.tools** - 工具容器镜像
   - 基于 Python 3.12-slim
   - 预装数据分析库
   - 安全配置

5. **docker/build-tools.sh** - 镜像构建脚本
   - 自动检查环境
   - 一键构建镜像

### 文档

6. **docs/DOCKER_TOOLS.md** - 主要文档
   - 功能介绍
   - 配置说明
   - 使用指南

7. **docs/DOCKER_MIGRATION_GUIDE.md** - 迁移指南
   - 代码调整建议
   - 迁移步骤
   - 回滚方案

8. **docs/DOCKER_TOOLS_FAQ.md** - 常见问题
   - Docker tools 和 files.py 的关系
   - 使用示例
   - 故障排查

9. **docs/DOCKER_FULL_ISOLATION.md** - 完全隔离方案
   - 架构设计
   - 实现细节
   - 方案对比

10. **docs/DOCKER_TOOLS_SUMMARY.md** - 本文档
    - 文件概览
    - 快速开始
    - 使用建议

### 示例

11. **examples/tools_comparison.py** - 对比示例
    - 性能测试
    - 安全性测试
    - 使用场景建议

## 🚀 快速开始

### 1. 构建 Docker 镜像

```bash
bash docker/build-tools.sh
```

### 2. 安装依赖

```bash
uv add docker
```

### 3. 配置环境变量

在 `.env` 中添加：

```env
# Docker 工具配置
DOCKER_IMAGE=deepagentschat-tools:latest
DOCKER_CPU_LIMIT=2.0
DOCKER_MEMORY_LIMIT=1g
DOCKER_NETWORK_MODE=none
DOCKER_TIMEOUT=30
```

### 4. 使用 Docker 工具

在 `app/agent.py` 中：

```python
# 替换
from app.tools import ALL_TOOLS

# 为
from app.tools_docker import ALL_TOOLS
```

### 5. 启动应用

```bash
# 容器会自动创建并启动
make dev
```

## 📊 架构说明

### 共享容器架构

```
FastAPI App
    ↓
SharedContainerManager (单例)
    ↓
Long-Running Container (deepagentschat-shared-tools)
    ├── Docker Volume: deepagentschat-workspace
    ├── /workspace/user-1/  # 用户1目录
    ├── /workspace/user-2/  # 用户2目录
    └── /workspace/user-3/  # 用户3目录
```

### 特点

- **共享容器**: 所有用户共享一个长期运行的容器
- **目录隔离**: 每个用户独立目录 `/workspace/{user_id}/`
- **文件系统**: 完全在容器内（Docker Volume）
- **自动重启**: 容器崩溃自动恢复
- **资源限制**: CPU/内存/网络可配置

## 🔄 与现有系统的关系

### tools.py vs tools_docker.py

| 特性 | tools.py | tools_docker.py |
|------|----------|-----------------|
| 执行环境 | 宿主机进程 | Docker 容器 |
| 文件存储 | 宿主机文件系统 | 容器内 Volume |
| 隔离性 | 进程隔离 | 容器隔离 |
| 性能 | 快 (~10-100ms) | 中等 (~100-500ms) |
| 安全性 | 中等 | 高 |
| 适用场景 | 开发环境 | 生产环境 |

### files.py 的兼容性

**当前状态**: files.py 仍使用宿主机文件系统

**未来计划**: 可选择修改 files.py 使用共享容器

```python
# 当前 (宿主机)
POST /files/upload -> 保存到 /tmp/user_files/{user_id}/

# 未来 (容器内)
POST /files/upload -> 通过 Docker API 复制到容器
```

## 🎯 使用建议

### 开发环境

```python
# 使用 tools.py (快速)
from app.tools import ALL_TOOLS
```

### 生产环境

```python
# 使用 tools_docker.py (安全)
from app.tools_docker import ALL_TOOLS
```

### 混合使用

```python
# 根据环境变量选择
import os
if os.getenv("USE_DOCKER_TOOLS") == "true":
    from app.tools_docker import ALL_TOOLS
else:
    from app.tools import ALL_TOOLS
```

## 📝 待办事项

### 可选改进

- [ ] 修改 files.py 使用共享容器
- [ ] 添加容器健康检查接口
- [ ] 添加容器资源监控
- [ ] 实现容器自动清理机制
- [ ] 添加更多单元测试
- [ ] 性能基准测试

### 文档改进

- [ ] 添加更多使用示例
- [ ] 添加故障排查指南
- [ ] 添加性能调优建议
- [ ] 添加安全最佳实践

## 🔐 安全考虑

### 已实现的安全措施

- ✅ 用户目录隔离
- ✅ 非 root 用户执行
- ✅ CPU/内存资源限制
- ✅ 网络隔离（默认）
- ✅ 移除所有 capabilities
- ✅ 禁止提权
- ✅ 路径遍历防护

### 建议的额外措施

- 定期更新基础镜像
- 定期清理用户数据
- 监控容器资源使用
- 设置磁盘配额
- 实施审计日志

## 📚 相关文档

- [主要文档](./DOCKER_TOOLS.md) - 功能介绍和配置
- [迁移指南](./DOCKER_MIGRATION_GUIDE.md) - 如何迁移
- [常见问题](./DOCKER_TOOLS_FAQ.md) - FAQ
- [完全隔离方案](./DOCKER_FULL_ISOLATION.md) - 架构设计

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**版本**: 1.0.0
**更新日期**: 2025-11-22
**状态**: 已完成核心功能，可用于生产环境
