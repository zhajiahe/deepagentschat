# 从零到一：构建现代化的 FastAPI + LangGraph 对话系统

> 一个集成了用户认证、LangGraph 对话系统和现代化前端的 FastAPI 后端模板项目

## 📖 项目简介

这是一个基于 FastAPI 和 LangGraph 的现代化后端项目模板，集成了完整的用户认证系统和对话系统。项目包含前后端代码，提供了一个完整的 AI 对话应用模板。

### ✨ 核心特性

- 🚀 **现代化后端**：FastAPI + LangGraph + SQLAlchemy
- 🔐 **用户认证**：JWT 令牌、用户注册/登录、权限管理
- 💬 **对话系统**：流式/非流式对话、会话管理、状态持久化
- 🎨 **现代化前端**：React + TypeScript + shadcn/ui 组件库
- 🧪 **测试覆盖**：后端集成测试、前端组件测试
- 🔍 **代码质量**：自动格式化、类型检查、Git 钩子

## 🎯 适用场景

- 快速构建 AI 对话应用
- 学习 FastAPI + React 开发
- 企业级项目模板
- LLM 应用后端开发

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
SILICONFLOW_API_KEY=your-api-key
SILICONFLOW_LLM_MODEL=Qwen/Qwen3-8B
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

# 启动前端（另一个终端）
cd web
pnpm dev
```

访问：
- 后端 API：http://localhost:8000/docs
- 前端应用：http://localhost:5173

## 🏗️ 项目结构

```
fastapi-template/
├── app/                    # 后端核心代码
│   ├── api/               # API 路由
│   ├── core/              # 核心配置
│   ├── models/            # 数据库模型
│   ├── schemas/           # 数据验证
│   └── main.py            # 应用入口
├── web/                   # 前端代码
│   ├── src/               # React 源代码
│   ├── package.json       # 前端依赖
│   └── tailwind.config.ts # 样式配置
├── tests/                 # 测试代码
├── alembic/               # 数据库迁移
├── .env                   # 环境变量
├── pyproject.toml         # 后端依赖
└── README.md
```

## 💡 主要功能

### 后端功能

- **用户认证**：注册、登录、JWT 认证、用户管理
- **对话系统**：创建会话、发送消息、流式响应、会话管理
- **用户设置**：个性化配置、主题切换、语言选择

### 前端功能

- **现代化 UI**：使用 shadcn/ui 组件库，统一设计语言
- **响应式设计**：支持桌面和移动端
- **实时交互**：流式消息显示、工具调用信息
- **状态管理**：Zustand 管理用户状态和会话

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

## 📚 API 端点

### 认证
- `POST /api/v1/auth/register` - 注册
- `POST /api/v1/auth/login` - 登录
- `GET /api/v1/auth/me` - 当前用户

### 对话
- `POST /api/v1/chat` - 发送消息
- `POST /api/v1/chat/stream` - 流式对话
- `GET /api/v1/conversations` - 会话列表

### 设置
- `GET /api/v1/users/settings` - 获取设置
- `PUT /api/v1/users/settings` - 更新设置

完整 API 文档：http://localhost:8000/docs

## 🎨 前端技术栈

- **框架**：React 18 + TypeScript
- **路由**：React Router
- **状态管理**：Zustand
- **UI 组件**：shadcn/ui (基于 Tailwind CSS + Radix UI)
- **样式**：Tailwind CSS
- **HTTP 请求**：Axios
- **构建工具**：Vite

## 🔧 开发指南

### 添加新功能

1. **后端**：
   - 创建模型和 Schema
   - 添加 API 路由
   - 运行数据库迁移
   - 编写测试

2. **前端**：
   - 创建 React 组件
   - 添加 API 调用
   - 使用 shadcn/ui 组件
   - 更新路由

### 自定义配置

- 编辑 `.env` 文件配置环境变量
- 修改 `app/core/config.py` 添加新配置
- 更新 `web/tailwind.config.ts` 自定义样式

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**Happy Coding! 🚀**

项目地址：[https://github.com/zhajiahe/fastapi-template](https://github.com/zhajiahe/fastapi-template)
