# Recursion Limit 问题修复

## 问题描述

错误信息：
```
Recursion limit of 25 reached without hitting a stop condition.
```

## 根本原因

虽然在创建 Agent 时设置了 `recursion_limit`：

```python
# app/agent.py
agent: Runnable = create_agent(
    model,
    tools=tools,
    checkpointer=checkpointer,
    middleware=[...],
).with_config({"recursion_limit": 1000})  # ❌ 这里设置的配置不会传递到运行时
```

但是，**`with_config()` 设置的配置只是默认配置**，当你在 `ainvoke()` 或 `astream_events()` 调用时传递了新的 `config` 参数，它会**覆盖**默认配置，而不是合并。

## 问题代码

```python
# app/api/chat.py
async for event in compiled_graph.astream_events(
    {"messages": [HumanMessage(content=request.message)]},
    config=config,  # ❌ 这个 config 没有包含 recursion_limit
    context=context,
    version="v2",
):
```

这里的 `config` 来自 `get_user_config()`：

```python
config: dict = {"configurable": {"thread_id": thread_id, "user_id": str(user_id)}}
```

它只包含 `thread_id` 和 `user_id`，**没有 `recursion_limit`**！

## 解决方案

有两种修复方案：

### 方案 1：在 config 中添加 recursion_limit（推荐）

修改 `get_user_config()` 函数，确保返回的 config 包含 `recursion_limit`：

```python
# app/api/chat.py
async def get_user_config(
    user_id: uuid.UUID, thread_id: str, db: AsyncSession
) -> tuple[dict, dict, dict[str, str | int | None]]:
    """获取用户配置"""
    config: dict = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(user_id)
        },
        "recursion_limit": 1000,  # ✅ 添加递归限制
    }
    context: dict = {}
    llm_params: dict[str, str | int | None] = {
        "llm_model": None,
        "api_key": None,
        "base_url": None,
        "max_tokens": 4096,
    }

    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = result.scalar_one_or_none()

    if user_settings:
        # LangGraph 配置和上下文
        config["configurable"].update(user_settings.config or {})
        context = user_settings.context or {}

        # 如果用户设置了自定义的 recursion_limit，使用用户的设置
        if user_settings.config and "recursion_limit" in user_settings.config:
            config["recursion_limit"] = user_settings.config["recursion_limit"]

        # ... 其余代码

    return config, context, llm_params
```

### 方案 2：合并配置（更灵活）

创建一个辅助函数来合并默认配置和运行时配置：

```python
# app/utils/config_helper.py
def merge_configs(base_config: dict, runtime_config: dict) -> dict:
    """合并 LangGraph 配置

    Args:
        base_config: 基础配置（来自 agent 创建时）
        runtime_config: 运行时配置（来自用户设置）

    Returns:
        合并后的配置
    """
    merged = base_config.copy()

    # 合并 configurable 字段
    if "configurable" in runtime_config:
        if "configurable" not in merged:
            merged["configurable"] = {}
        merged["configurable"].update(runtime_config["configurable"])

    # 合并其他字段（如 recursion_limit）
    for key, value in runtime_config.items():
        if key != "configurable":
            merged[key] = value

    return merged

# 在 chat.py 中使用
from app.utils.config_helper import merge_configs

# 定义默认配置
DEFAULT_CONFIG = {
    "recursion_limit": 1000,
    "configurable": {}
}

async def chat_stream(request: ChatRequest, current_user: CurrentUser, ...):
    # 获取用户配置
    config, context, llm_params = await get_user_config(current_user.id, thread_id, db)

    # 合并默认配置和用户配置
    merged_config = merge_configs(DEFAULT_CONFIG, config)

    async for event in compiled_graph.astream_events(
        {"messages": [HumanMessage(content=request.message)]},
        config=merged_config,  # ✅ 使用合并后的配置
        context=context,
        version="v2",
    ):
        # ...
```

### 方案 3：从环境变量读取（推荐用于全局配置）

```python
# app/core/config.py
class Settings(BaseSettings):
    # ... 其他配置

    # LangGraph 配置
    LANGGRAPH_RECURSION_LIMIT: int = 1000  # 递归限制
    LANGGRAPH_MAX_ITERATIONS: int = 100    # 最大迭代次数

# app/api/chat.py
from app.core.config import settings

async def get_user_config(...):
    config: dict = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(user_id)
        },
        "recursion_limit": settings.LANGGRAPH_RECURSION_LIMIT,  # ✅ 从配置读取
    }
    # ...
```

## 推荐实施方案

**结合方案 1 和方案 3**，既保证全局默认值，又允许用户自定义：

```python
# 1. 在 app/core/config.py 添加配置
class Settings(BaseSettings):
    # LangGraph 配置
    LANGGRAPH_RECURSION_LIMIT: int = 1000
    LANGGRAPH_MAX_ITERATIONS: int = 100

# 2. 修改 app/api/chat.py
from app.core.config import settings

async def get_user_config(
    user_id: uuid.UUID, thread_id: str, db: AsyncSession
) -> tuple[dict, dict, dict[str, str | int | None]]:
    """获取用户配置"""
    # 使用全局配置作为默认值
    config: dict = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": str(user_id)
        },
        "recursion_limit": settings.LANGGRAPH_RECURSION_LIMIT,
    }
    context: dict = {}
    llm_params: dict[str, str | int | None] = {
        "llm_model": None,
        "api_key": None,
        "base_url": None,
        "max_tokens": 4096,
    }

    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    user_settings = result.scalar_one_or_none()

    if user_settings:
        # LangGraph 配置和上下文
        config["configurable"].update(user_settings.config or {})
        context = user_settings.context or {}

        # 允许用户自定义递归限制
        if user_settings.config:
            if "recursion_limit" in user_settings.config:
                config["recursion_limit"] = user_settings.config["recursion_limit"]

        # ... 其余 LLM 参数逻辑

    return config, context, llm_params
```

## 验证修复

修复后，可以通过以下方式验证：

### 1. 日志验证

添加日志输出：

```python
async def chat_stream(...):
    config, context, llm_params = await get_user_config(current_user.id, thread_id, db)
    logger.info(f"Runtime config: {config}")  # ✅ 应该包含 recursion_limit: 1000

    async for event in compiled_graph.astream_events(..., config=config, ...):
        # ...
```

### 2. 测试用例

```python
# tests/api/test_chat.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_chat_stream_recursion_limit(async_client: AsyncClient, auth_headers: dict):
    """测试递归限制配置是否生效"""
    response = await async_client.post(
        "/api/chat/stream",
        json={
            "message": "执行一个需要多次工具调用的复杂任务",
        },
        headers=auth_headers,
    )

    # 流式响应不应该触发递归限制错误
    content = b""
    async for chunk in response.aiter_bytes():
        content += chunk

    # 验证没有错误
    assert b"Recursion limit" not in content
    assert b"error" not in content.lower()
```

### 3. 手动测试

发送一个需要多次工具调用的请求：

```bash
curl -X POST http://localhost:8000/api/chat/stream \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "请创建一个 Python 脚本，读取 data.csv，进行数据分析，生成图表，并写入 report.txt"
  }'
```

如果配置正确，应该能够顺利完成多个工具调用。

## 其他注意事项

### 1. 不要在 agent.py 中移除 with_config()

保留原有的 `with_config()` 作为备份：

```python
# app/agent.py
agent: Runnable = create_agent(
    model,
    tools=tools,
    checkpointer=checkpointer,
    middleware=[...],
).with_config({"recursion_limit": 1000})  # 保留作为默认值
```

### 2. 考虑添加最大迭代次数限制

除了 `recursion_limit`，还可以添加其他限制：

```python
config: dict = {
    "configurable": {
        "thread_id": thread_id,
        "user_id": str(user_id)
    },
    "recursion_limit": settings.LANGGRAPH_RECURSION_LIMIT,
    "max_iterations": settings.LANGGRAPH_MAX_ITERATIONS,  # 额外的安全措施
}
```

### 3. 为不同用户/场景设置不同限制

```python
# 在用户设置表中存储个性化的递归限制
class UserSettings(Base, BaseTableMixin):
    # ...
    recursion_limit: int = 1000  # 新增字段
    max_iterations: int = 100

# 在 get_user_config 中使用
if user_settings and user_settings.recursion_limit:
    config["recursion_limit"] = user_settings.recursion_limit
```

## 总结

**问题根源**：`with_config()` 设置的配置在传递 `config` 参数时被覆盖。

**解决方案**：在运行时 `config` 中显式包含 `recursion_limit`。

**最佳实践**：
1. 在 `get_user_config()` 中设置默认的 `recursion_limit`
2. 从全局配置读取默认值
3. 允许用户自定义（通过 UserSettings）
4. 在调试时记录实际使用的配置

---

**修复优先级**: 🔴 高（影响功能可用性）
**实施难度**: 🟢 简单（5分钟）
**测试重要性**: 🔴 高（需要充分测试）
