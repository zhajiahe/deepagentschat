# Fastapi Template Project

## Rule for Feedback
1. 在任何流程、任务、对话进行时，无论是询问、回复、或完成阶段性任务，皆必须调用 MCP mcp-feedback-enhanced。
2. 每当收到用户反馈，若反馈内容非空，必须再次调用 MCP mcp-feedback-enhanced，并根据反馈内容调整行为。
3. 仅当用户明确表示「结束」或「不再需要交互」时，才可停止调用 MCP mcp-feedback-enhanced，流程才算结束。
4. 除非收到结束指令，否则所有步骤都必须重复调用 MCP mcp-feedback-enhanced。
5. 完成任务前，必须使用 MCP mcp-feedback-enhanced 工具向用户询问反馈。

## Rule for Commit

**重要：仅在用户明确要求时才进行 Git 提交操作。**

### 提交规范（Commit Standards）：
遵循约定式提交格式，使用合适的 emoji 并创建描述性的中文提交信息。

### Commit Types:
- ✨ feat: 新功能
- 🐛 fix: Bug 修复
- 📝 docs: 文档修改
- ♻️ refactor: 代码重构
- 🧑‍💻 chore: 工具和维护
- 🎨 style: 代码格式、样式调整
- ⚡️ perf: 性能优化
- ✅ test: 测试相关
- 🗑️ chore: 删除文件或代码

### 提交步骤（仅在用户要求时执行）：
1. 运行 `git status` 查看变更
2. 使用 `git add` 添加文件到暂存区
3. 执行 `git commit -m` 提交，使用中文描述
4. 不包含 Claude 协作者信息

## Rule for Test
当实现测试脚本后，先执行测试后再编写文档

# Project Structure

## 项目概述

这是一个基于 FastAPI + SQLAlchemy 2.0+ 的现代化后端项目模板，集成了用户认证、数据库迁移、日志系统、代码质量检查等完整功能。现已扩展支持 LangGraph 对话系统，提供完整的会话管理和状态持久化能力。

## 核心技术栈

- **FastAPI**: 现代化的异步 Web 框架
- **SQLAlchemy 2.0+**: 异步 ORM
- **Alembic**: 数据库迁移工具
- **Pydantic**: 数据验证和设置管理
- **LangGraph**: 对话流程编排和状态管理
- **LangChain**: LLM 应用开发框架
- **Loguru**: 增强的日志系统
- **JWT**: 用户认证和授权
- **Bcrypt**: 密码加密

## 项目结构详解

```
fastapi-template/
├── app/                          # 应用核心代码
│   ├── api/                      # API 路由层
│   │   ├── users.py              # 用户管理 API
│   │   ├── chat.py               # 对话 API (LangGraph)
│   │   └── conversations.py     # 会话管理 API
│   ├── core/                     # 核心配置模块
│   │   ├── config.py             # 配置管理 (环境变量)
│   │   ├── database.py           # 数据库连接和会话管理
│   │   ├── deps.py               # 依赖注入 (认证、权限等)
│   │   ├── lifespan.py           # 应用生命周期管理
│   │   ├── security.py           # JWT 认证和密码加密
│   │   ├── graph.py              # LangGraph 图定义
│   │   └── checkpointer.py       # LangGraph 检查点管理
│   ├── middleware/               # 中间件
│   │   └── logging.py            # 请求日志中间件
│   ├── models/                   # SQLAlchemy 数据库模型
│   │   ├── base.py               # 基础模型和 Mixin
│   │   ├── user.py               # 用户模型
│   │   ├── conversation.py       # 会话模型
│   │   ├── message.py            # 消息模型
│   │   ├── execution_log.py      # 执行日志模型
│   │   └── user_settings.py      # 用户设置模型
│   ├── schemas/                  # Pydantic 数据模型
│   │   ├── user.py               # 用户 Schema
│   │   ├── chat.py               # 对话 Schema
│   │   ├── conversation.py       # 会话 Schema
│   │   └── user_settings.py      # 用户设置 Schema
│   ├── utils/                    # 工具函数
│   ├── sample_agent.py           # LangGraph 示例 Agent
│   └── main.py                   # 应用入口和路由注册
├── alembic/                      # 数据库迁移
│   ├── versions/                 # 迁移脚本版本
│   └── env.py                    # Alembic 配置
├── scripts/                      # 脚本工具
│   ├── create_superuser.py       # 创建超级管理员
│   └── init_db.py                # 初始化数据库
├── tests/                        # 测试代码
│   ├── integration/              # 集成测试
│   └── conftest.py               # Pytest 配置
├── logs/                         # 日志目录
├── .env                          # 环境变量配置
├── pyproject.toml                # 项目配置和依赖
├── Makefile                      # 常用命令集合
└── README.md                     # 项目说明文档
```

## 核心功能模块

### 1. 用户认证系统 (app/api/users.py, app/core/security.py)

- ✅ 用户注册与登录
- ✅ JWT 双令牌认证 (Access Token + Refresh Token)
- ✅ 密码加密 (Bcrypt)
- ✅ 基于角色的权限控制 (RBAC)
- ✅ 用户 CRUD 操作
- ✅ 分页查询和搜索

### 2. LangGraph 对话系统 (app/api/chat.py, app/core/graph.py)

- ✅ 异步对话接口（非流式 + SSE 流式）
- ✅ 对话停止功能（支持流式和非流式对话的中途停止）
- ✅ 会话生命周期（创建/查询/更新/删除/重置/硬删除）
- ✅ 消息历史与助手回复再生成
- ✅ 状态持久化（AsyncSqliteSaver）与时间旅行检查点
- ✅ 会话导出/导入与检查点清理
- ✅ 全文搜索与用户统计

### 3. 数据库层 (app/models/, app/core/database.py)

- ✅ SQLAlchemy 2.0+ 异步 ORM
- ✅ Alembic 数据库迁移
- ✅ 通用基础模型 (BaseTableMixin)
  - 自动 ID 生成
  - 创建/更新时间戳
  - 创建人/更新人
  - 逻辑删除支持
- ✅ 连接池管理
- ✅ 自动事务管理

### 4. 日志系统 (app/middleware/logging.py)

- ✅ Loguru 结构化日志
- ✅ 请求/响应日志中间件
- ✅ 日志文件自动轮转
- ✅ 错误日志单独记录
- ✅ 控制台彩色输出
- ✅ 请求 ID 追踪

### 5. 代码质量保证

- ✅ Ruff 代码检查和格式化
- ✅ MyPy 静态类型检查
- ✅ Pytest 单元测试和集成测试
- ✅ Pre-commit Git 钩子
- ✅ 测试覆盖率报告

### 6. 用户个性化设置 (app/models/user_settings.py)

- ✅ 独立 `user_settings` 表保存每位用户的偏好
- ✅ 默认 LLM 参数：模型（llm_model）、最大 Token（max_tokens）
- ✅ LangGraph 配置：config（JSON格式）、context（JSON格式）
- ✅ JSON `settings` 字段，便于扩展更多自定义配置
- ✅ `GET/PUT /api/v1/users/settings` API 直接读写

### 7. 级联删除机制

- ✅ Message 表外键约束指向 Conversation
- ✅ 删除会话时自动级联删除相关消息
- ✅ 数据库层面保证数据一致性

## API 端点概览

### 认证相关
- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `GET /api/v1/auth/me` - 获取当前用户信息
- `PUT /api/v1/auth/me` - 更新当前用户信息
- `POST /api/v1/auth/reset-password` - 修改密码

### 用户管理 (需要管理员权限)
- `GET /api/v1/users` - 获取用户列表 (分页)
- `GET /api/v1/users/{user_id}` - 获取用户详情
- `POST /api/v1/users` - 创建用户
- `PUT /api/v1/users/{user_id}` - 更新用户信息
- `DELETE /api/v1/users/{user_id}` - 删除用户

### 用户个性化设置
- `GET /api/v1/users/settings` - 获取当前用户偏好
- `PUT /api/v1/users/settings` - 更新 LLM 模型/最大 Token/配置/上下文

### 对话系统
- `POST /api/v1/chat` - 发送消息 (非流式)
- `POST /api/v1/chat/stream` - 发送消息 (SSE 流式)
- `POST /api/v1/chat/stop` - 停止正在进行的对话（流式/非流式）

### 会话管理
- `POST /api/v1/conversations` - 创建会话
- `GET /api/v1/conversations` - 获取会话列表
- `GET /api/v1/conversations/{thread_id}` - 获取会话详情
- `PATCH /api/v1/conversations/{thread_id}` - 更新会话
- `DELETE /api/v1/conversations/{thread_id}` - 删除会话（支持软删除/硬删除）
- `DELETE /api/v1/conversations/all` - 删除所有历史会话
- `POST /api/v1/conversations/{thread_id}/reset` - 重置会话并清空检查点
- `GET /api/v1/conversations/{thread_id}/messages` - 获取消息历史
- `GET /api/v1/conversations/{thread_id}/state` - 获取会话状态
- `GET /api/v1/conversations/{thread_id}/checkpoints` - 获取检查点历史
- `GET /api/v1/conversations/{thread_id}/export` - 导出会话
- `POST /api/v1/conversations/import` - 导入会话
- `POST /api/v1/conversations/search` - 搜索会话和消息
- `GET /api/v1/conversations/users/stats` - 获取个人统计

### 系统管理
- `GET /health` - 健康检查
- `GET /` - 根路径
- `GET /docs` - API 文档 (Swagger UI)
- `GET /redoc` - API 文档 (ReDoc)

## 开发工作流

### 1. 环境设置
```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 配置环境变量（参考 README 示例创建 .env 并填写内容）
```

### 2. 数据库迁移
```bash
# 创建迁移
make db-migrate msg="描述变更"

# 应用迁移
make db-upgrade

# 回滚迁移
make db-downgrade
```

### 3. 代码质量检查
```bash
# 代码检查
make lint

# 自动修复
make lint-fix

# 类型检查
make type-check

# 运行测试
make test
```

### 4. 启动开发服务器
```bash
make dev
# 或
uv run uvicorn app.main:app --reload
```

## 配置说明

### 环境变量 (.env)
```bash
# 数据库
DATABASE_URL=sqlite+aiosqlite:///./langgraph_app.db

# JWT 配置
SECRET_KEY=your-secret-key
REFRESH_SECRET_KEY=your-refresh-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 应用配置
APP_NAME=FastAPI-Template
DEBUG=true

# LangGraph 配置
CHECKPOINT_DB_PATH=./langgraph_app.db

# LangChain / SiliconFlow 模型
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.siliconflow.cn/v1
DEFAULT_LLM_MODEL=Qwen/Qwen3-8B
```

## 扩展建议

### 添加新的 API 端点
1. 在 `app/models/` 创建数据库模型
2. 在 `app/schemas/` 创建 Pydantic 模型
3. 在 `app/api/` 创建路由文件
4. 在 `app/main.py` 注册路由
5. 创建数据库迁移: `make db-migrate msg="添加新表"`
6. 编写测试用例

### 集成新的 LLM 提供商
1. 在 `app/sample_agent.py` 中修改 `get_agent()`（或替换为自定义 Agent 图）
2. 增加对应的环境变量（API Key、Base URL、模型名称等）
3. 更新 `pyproject.toml` 添加新供应商的 SDK 依赖

## 最佳实践

1. **异步优先**: 所有 I/O 操作使用异步
2. **类型注解**: 使用 Python 类型提示
3. **依赖注入**: 使用 FastAPI 的 Depends
4. **错误处理**: 使用 HTTPException 和自定义异常
5. **日志记录**: 使用 Loguru 记录关键操作
6. **测试覆盖**: 为核心功能编写测试
7. **代码审查**: 提交前运行 `make lint` 和 `make type-check`

## 常见问题

### Q: 如何切换到 PostgreSQL?
A: 修改 `.env` 中的 `DATABASE_URL` 为 `postgresql+asyncpg://user:pass@localhost/db`

### Q: 如何自定义 LangGraph 流程?
A: 编辑 `app/core/graph.py` 中的 `create_graph()` 函数

### Q: 如何添加新的中间件?
A: 在 `app/middleware/` 创建中间件，然后在 `app/main.py` 中注册

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交变更
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License
