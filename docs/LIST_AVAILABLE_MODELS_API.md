# 可用模型列表 API 文档

## 概述

提供了一个 API 端点用于获取系统支持的所有 LLM 模型列表及其详细配置信息。

**实现方式**: 基于 OpenAI SDK 动态获取模型提供商支持的所有模型，如果 API 调用失败则返回静态的备用列表。

## API 端点

### 获取可用模型列表

**端点**: `GET /api/v1/users/models/available`

**认证**: 需要 Bearer Token

**描述**: 返回系统支持的所有 LLM 模型及其配置信息

## 请求示例

### cURL

```bash
curl -X GET http://localhost:8000/api/v1/users/models/available \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Python

```python
import requests

url = "http://localhost:8000/api/v1/users/models/available"
headers = {"Authorization": "Bearer YOUR_TOKEN"}

response = requests.get(url, headers=headers)
data = response.json()

print(f"可用模型数量: {data['data']['total']}")
for model in data['data']['models']:
    print(f"- {model['name']}: {model['description']}")
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/api/v1/users/models/available', {
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN'
  }
});

const data = await response.json();
console.log('可用模型:', data.data.models);
```

## 响应格式

### 成功响应 (200 OK)

```json
{
  "success": true,
  "code": 200,
  "msg": "获取可用模型列表成功",
  "data": {
    "models": [
      {
        "id": "Qwen/Qwen3-8B",
        "name": "Qwen3-8B",
        "provider": "SiliconFlow",
        "description": "通义千问 3 - 8B 参数版本，适合日常对话和一般任务",
        "max_tokens": 4096,
        "recommended_max_tokens": 4096,
        "context_window": 32768,
        "capabilities": ["chat", "function_calling"],
        "pricing": {
          "input": 0.0,
          "output": 0.0
        }
      },
      {
        "id": "Qwen/Qwen3-72B",
        "name": "Qwen3-72B",
        "provider": "SiliconFlow",
        "description": "通义千问 3 - 72B 参数版本，适合复杂推理和专业任务",
        "max_tokens": 8192,
        "recommended_max_tokens": 8192,
        "context_window": 32768,
        "capabilities": ["chat", "function_calling", "advanced_reasoning"],
        "pricing": {
          "input": 0.0,
          "output": 0.0
        }
      }
      // ... 更多模型
    ],
    "total": 5,
    "default_model": "Qwen/Qwen3-8B",
    "providers": ["SiliconFlow"]
  }
}
```

### 错误响应

#### 未授权 (401/403)

```json
{
  "success": false,
  "code": 401,
  "msg": "未授权",
  "data": null
}
```

## 响应字段说明

### 顶层字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | boolean | 请求是否成功 |
| `code` | integer | HTTP 状态码 |
| `msg` | string | 响应消息 |
| `data` | object | 响应数据 |

### data 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `models` | array | 模型列表 |
| `total` | integer | 模型总数 |
| `default_model` | string | 默认模型 ID |
| `providers` | array | 提供商列表 |

### models 数组中的模型对象

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 模型唯一标识符（用于 API 调用） |
| `name` | string | 模型显示名称 |
| `provider` | string | 模型提供商 |
| `description` | string | 模型描述 |
| `max_tokens` | integer | 最大输出 token 数 |
| `recommended_max_tokens` | integer | 推荐的最大 token 数 |
| `context_window` | integer | 上下文窗口大小 |
| `capabilities` | array | 模型能力列表 |
| `pricing` | object | 定价信息 |

### capabilities 能力标签

| 标签 | 说明 |
|------|------|
| `chat` | 支持对话 |
| `function_calling` | 支持函数调用 |
| `code_generation` | 支持代码生成 |
| `advanced_reasoning` | 支持高级推理 |
| `instruction_following` | 支持指令遵循 |

### pricing 定价对象

| 字段 | 类型 | 说明 |
|------|------|------|
| `input` | float | 输入 token 价格（每 1K tokens） |
| `output` | float | 输出 token 价格（每 1K tokens） |

## 使用场景

### 1. 在前端显示模型选择器

```javascript
// 获取模型列表
const response = await fetch('/api/v1/users/models/available', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const { data } = await response.json();

// 渲染下拉选择器
const select = document.getElementById('model-select');
data.models.forEach(model => {
  const option = document.createElement('option');
  option.value = model.id;
  option.textContent = `${model.name} - ${model.description}`;
  if (model.id === data.default_model) {
    option.selected = true;
  }
  select.appendChild(option);
});
```

### 2. 根据任务类型推荐模型

```python
def recommend_model(task_type: str, models: list) -> dict:
    """根据任务类型推荐最合适的模型"""
    if task_type == "code":
        # 推荐支持代码生成的模型
        code_models = [m for m in models if "code_generation" in m["capabilities"]]
        return code_models[0] if code_models else models[0]

    elif task_type == "reasoning":
        # 推荐支持高级推理的大模型
        reasoning_models = [m for m in models if "advanced_reasoning" in m["capabilities"]]
        # 按参数量排序（假设名称中包含参数信息）
        reasoning_models.sort(key=lambda x: x["max_tokens"], reverse=True)
        return reasoning_models[0] if reasoning_models else models[0]

    else:
        # 默认返回默认模型
        return next((m for m in models if m["id"] == "Qwen/Qwen3-8B"), models[0])

# 使用示例
response = requests.get(url, headers=headers)
data = response.json()
models = data["data"]["models"]

recommended = recommend_model("code", models)
print(f"推荐模型: {recommended['name']}")
```

### 3. 显示模型详情卡片

```javascript
function renderModelCard(model) {
  return `
    <div class="model-card">
      <h3>${model.name}</h3>
      <p class="provider">提供商: ${model.provider}</p>
      <p class="description">${model.description}</p>
      <div class="specs">
        <span>最大 Tokens: ${model.max_tokens}</span>
        <span>上下文窗口: ${model.context_window}</span>
      </div>
      <div class="capabilities">
        ${model.capabilities.map(cap => `<span class="badge">${cap}</span>`).join('')}
      </div>
      <button onclick="selectModel('${model.id}')">选择此模型</button>
    </div>
  `;
}
```

### 4. 验证用户选择的模型是否可用

```python
def validate_model(model_id: str, available_models: list) -> bool:
    """验证模型 ID 是否在可用列表中"""
    model_ids = [m["id"] for m in available_models]
    return model_id in model_ids

# 使用示例
user_selected_model = "Qwen/Qwen3-72B"
response = requests.get(url, headers=headers)
data = response.json()

if validate_model(user_selected_model, data["data"]["models"]):
    print("模型可用，可以继续")
else:
    print("模型不可用，请选择其他模型")
```

## 与用户设置 API 结合使用

### 完整工作流程

```python
import requests

class ModelManager:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}

    def get_available_models(self):
        """获取可用模型列表"""
        response = requests.get(
            f"{self.base_url}/api/v1/users/models/available",
            headers=self.headers
        )
        return response.json()["data"]

    def update_user_model(self, model_id: str, max_tokens: int):
        """更新用户的模型设置"""
        response = requests.put(
            f"{self.base_url}/api/v1/users/settings",
            headers=self.headers,
            json={
                "llm_model": model_id,
                "max_tokens": max_tokens
            }
        )
        return response.json()

    def switch_model(self, model_name: str):
        """切换到指定模型"""
        # 1. 获取可用模型列表
        models_data = self.get_available_models()

        # 2. 查找目标模型
        target_model = next(
            (m for m in models_data["models"] if m["name"] == model_name),
            None
        )

        if not target_model:
            raise ValueError(f"模型 {model_name} 不可用")

        # 3. 更新用户设置
        result = self.update_user_model(
            target_model["id"],
            target_model["recommended_max_tokens"]
        )

        print(f"已切换到模型: {target_model['name']}")
        return result

# 使用示例
manager = ModelManager("http://localhost:8000", "your-token")

# 列出所有可用模型
models_data = manager.get_available_models()
print(f"可用模型: {[m['name'] for m in models_data['models']]}")

# 切换到大模型
manager.switch_model("Qwen3-72B")
```

## 工作原理

### 动态获取模型列表

API 使用 OpenAI SDK 从配置的模型提供商动态获取模型列表：

```python
# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_API_BASE,  # 例如: https://api.siliconflow.cn/v1
)

# 获取模型列表
models_response = client.models.list()
```

### 模型属性推断

系统会根据模型 ID 自动推断模型的属性：

- **参数量**: 从模型名称中提取（如 "72B", "8B"）
- **能力标签**: 根据模型名称关键词判断
  - `Qwen` 或 `gpt` → 支持函数调用
  - `DeepSeek` 或 `code` → 支持代码生成
  - `Instruct` → 支持指令遵循
  - `72B` 或 `70B` → 支持高级推理

### 备用机制

如果 OpenAI SDK 调用失败（例如网络问题、API 密钥错误），系统会自动返回静态的备用模型列表，确保 API 始终可用。

## 配置要求

在 `.env` 文件中配置：

```bash
# OpenAI API 配置（或兼容的提供商）
OPENAI_API_KEY=your-api-key
OPENAI_API_BASE=https://api.siliconflow.cn/v1
DEFAULT_LLM_MODEL=Qwen/Qwen3-8B
```

## 扩展模型列表

### 方法 1: 自动获取（推荐）

如果模型提供商支持 OpenAI 兼容的 API，只需确保 `OPENAI_API_BASE` 配置正确，系统会自动获取所有可用模型。

### 方法 2: 修改备用列表

如果需要自定义备用列表，在 `app/api/users.py` 的 `list_available_models` 函数的 `fallback_models` 中添加：

```python
{
    "id": "your-provider/your-model",
    "name": "Your Model Name",
    "provider": "Your Provider",
    "description": "模型描述",
    "max_tokens": 4096,
    "recommended_max_tokens": 4096,
    "context_window": 32768,
    "capabilities": ["chat"],
    "pricing": {"input": 0.0, "output": 0.0},
    "created": 0,
}
```

## 最佳实践

1. **缓存模型列表**: 在前端缓存模型列表，避免频繁请求
2. **显示推荐配置**: 使用 `recommended_max_tokens` 作为默认值
3. **能力匹配**: 根据任务需求筛选具有特定能力的模型
4. **价格展示**: 在 UI 中显示定价信息，帮助用户做出选择
5. **默认模型**: 使用 `default_model` 作为新用户的初始配置

## 注意事项

- 该 API 需要用户认证
- 模型列表是静态配置的，如需动态获取需要集成模型提供商的 API
- 定价信息需要根据实际情况更新
- 建议定期更新模型列表以包含最新的模型

## 相关 API

- [用户设置 API](./USER_SETTINGS_API.md) - 更新用户的模型配置
- [对话 API](./CHAT_API.md) - 使用配置的模型进行对话
- [动态图配置](./DYNAMIC_GRAPH_SUMMARY.md) - 了解模型参数如何动态生效
