# 贡献指南

感谢你对 DeepAgentsChat 项目的关注！我们欢迎任何形式的贡献，包括但不限于：

- 🐛 报告 Bug
- ✨ 提出新功能建议
- 📝 改进文档
- 💻 提交代码

## 📋 目录

- [开发环境设置](#开发环境设置)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [Pull Request 流程](#pull-request-流程)
- [测试](#测试)

## 🛠️ 开发环境设置

### 1. Fork 并克隆项目

```bash
# Fork 项目到你的 GitHub 账号
# 然后克隆到本地
git clone https://github.com/YOUR_USERNAME/deepagentschat.git
cd deepagentschat
```

### 2. 安装依赖

```bash
# 后端依赖
uv sync

# 前端依赖
cd web
pnpm install
cd ..
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填写必要的配置
```

### 4. 初始化数据库

```bash
make db-upgrade
uv run python scripts/create_superuser.py
```

### 5. 安装 pre-commit hooks

```bash
pre-commit install
```

## 📏 代码规范

### Python 代码规范

我们使用以下工具确保代码质量：

- **Ruff**: 代码格式化和 lint 检查
- **MyPy**: 类型检查
- **pytest**: 单元测试

#### 代码风格

- 使用 Python 3.12+ 特性
- 遵循 PEP 8 规范
- 行长度限制：120 字符
- 使用类型注解
- 使用异步编程（async/await）

#### 示例

```python
from typing import Any

async def get_user(user_id: int) -> dict[str, Any]:
    """获取用户信息

    Args:
        user_id: 用户 ID

    Returns:
        dict: 用户信息字典
    """
    # 实现代码
    pass
```

### TypeScript/React 代码规范

- 使用 TypeScript 严格模式
- 遵循 React Hooks 规范
- 使用函数式组件
- 使用 Tailwind CSS 进行样式设计

### 运行代码检查

```bash
# 后端
make lint          # 运行 ruff 检查
make type-check    # 运行 mypy 类型检查
make test          # 运行测试

# 前端
cd web
pnpm lint          # 运行 ESLint
pnpm type-check    # 运行 TypeScript 检查
```

## 📝 提交规范

我们使用 [约定式提交](https://www.conventionalcommits.org/zh-hans/) 规范，并使用 emoji 前缀。

### 提交格式

```
<emoji> <type>: <subject>

[optional body]

[optional footer]
```

### 提交类型

| Emoji | Type | 说明 | 示例 |
|-------|------|------|------|
| ✨ | feat | 新功能 | `✨ feat: 添加用户导出功能` |
| 🐛 | fix | Bug 修复 | `🐛 fix: 修复登录页面样式问题` |
| 📝 | docs | 文档修改 | `📝 docs: 更新 API 文档` |
| ♻️ | refactor | 代码重构 | `♻️ refactor: 优化数据库查询逻辑` |
| 🧑‍💻 | chore | 工具和维护 | `🧑‍💻 chore: 更新依赖版本` |
| 🎨 | style | 代码格式 | `🎨 style: 格式化代码` |
| ⚡️ | perf | 性能优化 | `⚡️ perf: 优化文件上传速度` |
| ✅ | test | 测试相关 | `✅ test: 添加用户认证测试` |
| 🗑️ | chore | 删除文件 | `🗑️ chore: 删除废弃的工具函数` |

### 提交示例

```bash
# 好的提交
git commit -m "✨ feat: 添加文件批量上传功能"
git commit -m "🐛 fix: 修复流式对话中断问题"
git commit -m "📝 docs: 更新部署文档"

# 不好的提交
git commit -m "update"
git commit -m "fix bug"
git commit -m "修改代码"
```

## 🔄 Pull Request 流程

### 1. 创建分支

```bash
# 从 main 分支创建新分支
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
```

### 2. 开发和提交

```bash
# 进行开发
# ...

# 提交更改
git add .
git commit -m "✨ feat: 你的功能描述"
```

### 3. 推送到 GitHub

```bash
git push origin feature/your-feature-name
```

### 4. 创建 Pull Request

1. 访问你的 Fork 仓库
2. 点击 "New Pull Request"
3. 填写 PR 标题和描述
4. 等待 CI 检查通过
5. 等待代码审查

### PR 标题格式

```
<emoji> <type>: <简短描述>
```

示例：
- `✨ feat: 添加文件批量上传功能`
- `🐛 fix: 修复流式对话中断问题`

### PR 描述模板

```markdown
## 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 代码重构
- [ ] 性能优化
- [ ] 测试
- [ ] 其他

## 变更说明
简要描述你的更改内容

## 测试
描述如何测试你的更改

## 相关 Issue
Closes #issue_number
```

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
make test

# 运行特定测试文件
pytest tests/test_auth.py

# 运行特定测试函数
pytest tests/test_auth.py::test_login
```

### 编写测试

- 为新功能添加测试
- 为 Bug 修复添加回归测试
- 确保测试覆盖率不降低

### 测试示例

```python
import pytest
from app.main import app
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_login():
    """测试用户登录"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test123"}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()
```

## 📋 代码审查清单

在提交 PR 前，请确保：

- [ ] 代码遵循项目规范
- [ ] 所有测试通过
- [ ] 添加了必要的文档
- [ ] 更新了 CHANGELOG.md（如果是重要更改）
- [ ] 提交信息符合规范
- [ ] 代码已经过 lint 和类型检查
- [ ] 没有遗留的 console.log 或 print 语句
- [ ] 没有提交敏感信息（API 密钥、密码等）

## 🤝 行为准则

- 尊重他人
- 保持友好和专业
- 接受建设性批评
- 关注项目的最佳利益

## 💬 获取帮助

如果你有任何问题：

- 📖 查看 [文档](./README.md)
- 💬 在 [Discussions](https://github.com/zhajiahe/deepagentschat/discussions) 提问
- 🐛 在 [Issues](https://github.com/zhajiahe/deepagentschat/issues) 报告问题

## 📄 许可证

通过贡献代码，你同意你的贡献将在 [MIT License](./LICENSE) 下发布。

---

**感谢你的贡献！** 🎉
