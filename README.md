<p align="center">
  <img src="web/public/readme.svg" alt="DeepAgentsChat Logo" width="300">
</p>

<p align="center">
  <a href="https://github.com/zhajiahe/deepagentschat/releases/tag/v0.4.0"><img src="https://img.shields.io/badge/version-0.4.0-blue.svg" alt="Version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-green.svg" alt="FastAPI"></a>
  <a href="https://reactjs.org/"><img src="https://img.shields.io/badge/React-18+-blue.svg" alt="React"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License"></a>
</p>

<p align="center">
  <strong>一个生产级的 AI Agent 对话应用全栈模板</strong>
</p>

<p align="center">
  集成 LangChain Agents、DeepAgents 中间件、多用户隔离、文件系统沙箱、流式对话和现代化前端
</p>

---

## 📖 项目简介

**DeepAgentsChat** 是一个基于 FastAPI + LangChain Agents + React 的现代化全栈 AI 应用模板。它不仅提供了完整的用户认证和对话系统，还集成了 **DeepAgents 中间件**，支持文件系统操作、工具调用、待办事项管理和对话摘要等高级功能。

### ✨ 核心特性

- 🤖 **LangChain Agents**：基于 LangChain v1 的 `create_agent` API，支持工具调用和中间件扩展
- 🔧 **DeepAgents 中间件**：集成 `FilesystemMiddleware`、`TodoListMiddleware`、`SummarizationMiddleware`
- 🗂️ **多用户文件隔离**：每个用户拥有独立的虚拟文件系统（`/tmp/{user_id}`）
- 🏗️ **多种 Sandbox Backend**：支持 `StateSandboxBackend`（内存）、`FilesystemSandboxBackend`（本地）、`DockerSandboxBackend`（容器）
- 🔐 **完整用户认证**：JWT 双令牌、用户注册/登录、权限管理
- 💬 **流式对话系统**：SSE 流式响应、会话管理、状态持久化（LangGraph Checkpointer）
- 📁 **文件浏览器**：右侧可折叠面板，支持文件上传/下载/删除/预览
- 🎨 **现代化前端**：React 18 + TypeScript + shadcn/ui + Tailwind CSS
- 🧪 **测试覆盖**：集成测试、代码质量检查（Ruff、MyPy）
- 🔍 **MCP 集成**：支持 LangChain MCP Adapters，可连接外部工具和服务

### 🎯 适用场景

- 🚀 快速构建生产级 AI Agent 应用
- 📚 学习 LangChain Agents + FastAPI + React 全栈开发
- 🏢 企业级 AI 应用后端模板
- 🔬 LLM 应用研发和原型验证

## 🚀 快速开始

### 1. 环境要求

- Python 3.12+
- Node.js 18+ (用于前端)
- uv（推荐的 Python 包管理器）

### 2. 克隆并安装

```bash
# 克隆项目
git clone https://github.com/zhajiahe/fastapi-template.git
cd fastapi-template

# 安装后端依赖
uv sync

# 安装前端依赖
cd web
pnpm install
cd ..

# 构建前端文件
bash deloey.sh
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./langgraph_app.db

# JWT 配置
SECRET_KEY=your-secret-key-change-in-production
REFRESH_SECRET_KEY=your-refresh-secret-key-change-in-production

# 应用配置
APP_NAME=FastAPI-Template
DEBUG=true

# LLM 配置（可选）
OPENAI_API_KEY=your-api-key
DEFAULT_LLM_MODEL=Qwen/Qwen3-8B
```

### 4. 初始化数据库

```bash
# 运行数据库迁移
make db-upgrade

# 创建超级管理员
uv run python scripts/create_superuser.py
```

### 5. 启动服务

```bash
# 启动后端（另一个终端）
make dev
```

访问：
- 后端 API：http://localhost:8000/docs
- 前端应用：http://localhost:8000/web

## 🏗️ 项目架构

```
fastapi-template/
├── app/                          # 后端核心代码
│   ├── api/                      # API 路由层
│   │   ├── chat.py               # 对话接口（流式/非流式）
│   │   ├── conversations.py      # 会话管理
│   │   ├── files.py              # 文件管理（上传/下载/删除）
│   │   └── users.py              # 用户认证和管理
│   ├── backends/                 # Sandbox Backend 实现
│   │   ├── state_sandbox.py      # 内存沙箱
│   │   ├── filesystem_sandbox.py # 文件系统沙箱
│   │   └── docker_sandbox.py     # Docker 容器沙箱
│   ├── core/                     # 核心配置和依赖
│   │   ├── config.py             # 环境配置
│   │   ├── database.py           # 数据库连接
│   │   ├── security.py           # JWT 认证
│   │   └── lifespan.py           # 应用生命周期
│   ├── models/                   # SQLAlchemy 数据库模型
│   ├── schemas/                  # Pydantic 数据验证
│   ├── agent.py                  # LangChain Agent 定义
│   └── main.py                   # FastAPI 应用入口
├── web/                          # 前端代码（React + TypeScript）
│   ├── src/
│   │   ├── pages/                # 页面组件
│   │   ├── components/           # UI 组件（Sidebar、FileBrowser 等）
│   │   ├── stores/               # Zustand 状态管理
│   │   └── hooks/                # 自定义 React Hooks
│   └── public/                   # 静态资源（logo、favicon）
├── tests/                        # 测试代码
├── scripts/                      # 工具脚本
├── alembic/                      # 数据库迁移
├── .env                          # 环境变量配置
├── pyproject.toml                # Python 依赖（uv）
└── Makefile                      # 常用命令快捷方式
```

## 💡 核心功能

### 🤖 AI Agent 能力

- **工具调用**：支持数学计算、文件系统操作、MCP 工具等
- **待办事项管理**：Agent 可自主创建和管理任务列表
- **对话摘要**：自动总结长对话，节省 token
- **文件系统操作**：读写文件、执行命令（沙箱隔离）
- **流式响应**：逐 token 输出，提升用户体验

### 🔐 用户系统

- **JWT 双令牌认证**：Access Token + Refresh Token
- **用户注册/登录**：邮箱/用户名登录
- **权限管理**：基于角色的访问控制（RBAC）
- **个性化设置**：LLM 模型选择、参数配置

### 📁 文件管理

- **多用户隔离**：每个用户独立的虚拟文件系统
- **文件浏览器**：可视化文件管理界面
- **上传/下载**：支持文件上传和下载
- **文件预览**：支持文本文件在线预览

### 🎨 前端体验

- **现代化 UI**：基于 shadcn/ui 和 Tailwind CSS
- **流式消息显示**：实时显示 AI 回复
- **工具调用可视化**：展示 Agent 的思考过程
- **响应式设计**：适配桌面和移动端

## 🛠️ 常用命令

### 后端命令

```bash
make dev           # 启动开发服务器
make test          # 运行测试
make lint          # 代码检查
make db-upgrade    # 数据库迁移
make clean         # 清理
```

### 前端命令

```bash
cd web
pnpm dev          # 开发服务器
pnpm build        # 构建生产版本
pnpm lint         # 代码检查
```

## 📚 API 文档

项目提供完整的 RESTful API，包括：

- **认证 API**：用户注册、登录、JWT 刷新
- **对话 API**：流式/非流式对话、停止对话
- **会话管理 API**：创建、查询、更新、删除会话
- **文件管理 API**：上传、下载、删除、列出文件
- **用户设置 API**：个性化配置管理

**完整 API 文档**：启动服务后访问 http://localhost:8000/docs（Swagger UI）或 http://localhost:8000/redoc（ReDoc）

## 🎨 技术栈

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **FastAPI** | 0.115+ | 异步 Web 框架 |
| **LangChain** | 1.0+ | Agent 框架和工具调用 |
| **DeepAgents** | Latest | 中间件（文件系统、待办事项、摘要） |
| **SQLAlchemy** | 2.0+ | 异步 ORM |
| **Alembic** | Latest | 数据库迁移 |
| **Pydantic** | 2.0+ | 数据验证 |
| **Loguru** | Latest | 结构化日志 |
| **JWT** | - | 用户认证 |

### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **React** | 18+ | UI 框架 |
| **TypeScript** | 5+ | 类型安全 |
| **Vite** | 5+ | 构建工具 |
| **Zustand** | Latest | 状态管理 |
| **shadcn/ui** | Latest | UI 组件库 |
| **Tailwind CSS** | 3+ | 样式框架 |
| **Axios** | Latest | HTTP 客户端 |

## 📄 许可证

本项目采用 [MIT License](./LICENSE) 开源协议。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [LangChain](https://www.langchain.com/) - LLM 应用开发框架
- [DeepAgents](https://github.com/deepagents/deepagents) - Agent 中间件库
- [shadcn/ui](https://ui.shadcn.com/) - 优雅的 React 组件库

## 🙏🙏 特别致谢
- cursor

---

<p align="center">
  <strong>⭐ 如果这个项目对你有帮助，请给个 Star！</strong>
</p>

<p align="center">
  <a href="https://github.com/zhajiahe/deepagentschat">项目地址</a> •
  <a href="https://github.com/zhajiahe/deepagentschat/issues">报告问题</a> •
  <a href="https://github.com/zhajiahe/deepagentschat/discussions">讨论</a>
</p>
