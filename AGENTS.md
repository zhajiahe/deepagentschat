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

## 开发工作流

### 1. 环境设置
```bash
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装依赖
uv sync

# 激活环境
source .venv/bin/activate

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
1. 在 `app/agent.py` 中修改 `get_agent()`（或替换为自定义 Agent 图）
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

## Agent 配置

### 使用 DeepAgents 默认后端
项目使用 deepagents 的默认 StateBackend，无需自定义文件系统实现。

在 `app/agent.py` 中：
```python
# 使用 deepagents 默认 backend（不需要显式配置）
# deepagents 的 create_agent 会自动使用 StateBackend 作为默认后端
agent: Runnable = create_agent(
    model,
    tools=[math_tool, *mcp_tools],
    checkpointer=checkpointer,
    middleware=[
        TodoListMiddleware(),
        PatchToolCallsMiddleware(),
        SummarizationMiddleware(model=model, max_tokens_before_summary=170000, messages_to_keep=10),
    ],
).with_config({"recursion_limit": 1000})
```

### 文件管理
- **用户文件隔离**: `/tmp/user_files/{user_id}` - 每个用户独立存储空间
- **工具虚拟环境**: `/tmp/user_files/.tools_venv` - 独立 Python 环境,所有用户共享
- **文件浏览器**: 支持子文件夹导航、多格式预览(Markdown/JSON/代码/CSV)
- **API 接口**: `app/api/files.py` 提供完整的文件操作 API

## Agent 工具系统

### 工具实现(app/tools.py)
- 使用 `@tool` 装饰器和 `ToolRuntime` 实现用户上下文注入
- **shell_exec**: 执行 Bash 命令,自动使用独立工具虚拟环境
- **write_file**: 写入文件,支持覆盖/追加模式
- **read_file**: 读取文件,自动截断大文件

### 独立虚拟环境
- 工具执行使用独立 Python 环境,避免污染项目环境
- 通过 `.pth` 文件链接项目依赖,轻量且快速
- 首次使用自动创建,后续无额外开销

### 用户隔离
- 通过 `ToolRuntime[UserContext]` 自动注入 `user_id`
- 所有文件操作限制在用户目录内
- 支持公共目录(user_id 为空时)

## 常见问题
### Q: 如何自定义 Agent 工具?
A: 在 `app/tools.py` 中使用 `@tool` 装饰器创建函数,添加到 `ALL_TOOLS` 列表

### Q: 工具虚拟环境在哪里?
A: `/tmp/user_files/.tools_venv`,所有用户共享,与项目环境隔离

### Q: 如何添加新的中间件?
A: 在 `app/agent.py` 的 `create_agent()` 中添加到 `middleware` 列表
