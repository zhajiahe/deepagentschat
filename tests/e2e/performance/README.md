# 性能测试文档

## 概述

本目录包含用于测试 FastAPI 应用并发性能的工具和脚本，特别关注多用户同时进行 chat 的场景。

## 文件说明

- `locust.conf` - Locust 配置文件
- `locustfile.py` - Locust 测试场景定义
- `analyze_performance.py` - 详细的性能分析脚本
- `README.md` - 本文档

## 前置条件

### 1. 安装依赖

```bash
# 安装 Locust（负载测试工具）
pip install locust

# 或使用 uv
uv pip install locust

# 安装 httpx（用于性能分析脚本）
pip install httpx
```

### 2. 启动应用

```bash
# 确保应用正在运行
cd /data2/zhanghuaao/project/DeepAgentChat
uv run uvicorn app.main:app --reload
```

## 使用方法

### 方法 1: 使用 Locust（推荐）

Locust 提供 Web UI 和实时监控功能。

#### 启动 Locust

```bash
cd tests/e2e/performance
locust -f locustfile.py --config locust.conf
```

#### 使用 Web UI

1. 打开浏览器访问 `http://localhost:8089`
2. 设置参数：
   - Number of users: 5
   - Spawn rate: 1 (每秒启动 1 个用户)
   - Host: http://localhost:8000
3. 点击 "Start swarming" 开始测试
4. 实时查看性能指标和图表

#### 命令行模式（无 UI）

```bash
locust -f locustfile.py \
  --host=http://localhost:8000 \
  --users=5 \
  --spawn-rate=1 \
  --run-time=30s \
  --headless \
  --html=report.html
```

参数说明：
- `--users`: 并发用户数
- `--spawn-rate`: 每秒启动的用户数
- `--run-time`: 测试运行时间
- `--headless`: 无 UI 模式
- `--html`: 生成 HTML 报告

### 方法 2: 使用性能分析脚本

提供更详细的性能分析和瓶颈识别。

```bash
cd tests/e2e/performance
python analyze_performance.py
```

该脚本会：
1. 创建 5 个并发用户
2. 每个用户发送 5 条消息
3. 测量响应时间
4. 分析性能瓶颈
5. 生成详细报告

## 测试场景

### Locust 测试场景

模拟真实用户行为，包括：

1. **用户注册和登录** (on_start)
   - 每个用户使用唯一的用户名
   - 自动获取 access_token

2. **发送聊天消息** (权重 3)
   - 随机选择消息内容
   - 自动管理 thread_id
   - 测量响应时间

3. **获取会话列表** (权重 1)
   - 查询用户的所有会话

4. **获取用户设置** (权重 1)
   - 读取用户配置

### 性能分析脚本场景

更系统的测试流程：

1. 并发创建 5 个用户
2. 每个用户依次发送 5 条消息
3. 收集所有响应时间数据
4. 计算统计指标
5. 识别性能瓶颈

## 性能指标

### 关键指标

1. **响应时间**
   - 平均响应时间
   - 中位数 (P50)
   - P90, P95, P99 百分位数
   - 最小/最大响应时间

2. **吞吐量**
   - RPS (Requests Per Second)
   - 每用户平均 RPS

3. **成功率**
   - 成功请求数
   - 失败请求数
   - 成功率百分比

4. **并发效率**
   - 并发用户下的性能表现
   - 资源利用率

## 性能基准

### 预期性能

| 指标 | 良好 | 可接受 | 需优化 |
|------|------|--------|--------|
| 平均响应时间 | < 1s | 1-2s | > 2s |
| P95 响应时间 | < 2s | 2-5s | > 5s |
| 成功率 | > 99% | 95-99% | < 95% |
| RPS | > 10 | 5-10 | < 5 |

### 性能瓶颈识别

脚本会自动识别以下瓶颈：

1. **LLM API 响应慢**
   - 症状：平均响应时间 > 2s
   - 建议：优化 API 调用、增加超时

2. **数据库性能问题**
   - 症状：查询接口响应慢
   - 建议：优化查询、增加索引

3. **并发资源竞争**
   - 症状：并发效率低
   - 建议：检查连接池、锁竞争

4. **内存/CPU 瓶颈**
   - 症状：响应时间随用户数增加
   - 建议：增加资源、优化代码

## 结果分析

### Locust 报告

Locust 生成的 HTML 报告包含：
- 请求统计表
- 响应时间分布图
- RPS 时间序列图
- 失败率图表

### 性能分析脚本输出

```
📊 性能分析报告
==================================================

1. 用户统计:
   总用户数: 5
   成功用户: 5
   失败用户: 0

2. 消息统计:
   总消息数: 25
   成功消息: 25
   失败消息: 0
   成功率: 100.00%

3. 响应时间分析:
   平均响应时间: 1234.56ms
   中位数响应时间: 1200.00ms
   最小响应时间: 800.00ms
   最大响应时间: 2000.00ms
   标准差: 250.00ms
   P50: 1200.00ms
   P90: 1800.00ms
   P95: 1900.00ms
   P99: 1980.00ms

4. 吞吐量分析:
   总耗时: 15.23秒
   平均 RPS: 1.64
   平均每用户耗时: 3.05秒

5. 性能瓶颈分析:
   ℹ️  轻微瓶颈: 平均响应时间超过 1 秒
      建议:
      - 监控 LLM API 响应时间

6. 并发效率:
   每用户平均 RPS: 0.33
   ✅ 并发效率良好
```

## 优化建议

### 1. LLM API 优化

```python
# 使用流式响应减少等待时间
POST /api/v1/chat/stream

# 配置合理的超时
client = OpenAI(timeout=30.0)
```

### 2. 数据库优化

```python
# 使用连接池
DATABASE_URL = "sqlite+aiosqlite:///./app.db?pool_size=20"

# 添加索引
CREATE INDEX idx_conversation_user_id ON conversation(user_id);
```

### 3. 缓存优化

```python
# 缓存用户设置
@lru_cache(maxsize=100)
def get_user_settings(user_id: str):
    ...
```

### 4. 异步处理

```python
# 使用异步任务处理耗时操作
background_tasks.add_task(process_message, message)
```

## 故障排查

### 问题 1: 连接被拒绝

```
Error: Connection refused
```

**解决方案**: 确保应用正在运行

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 问题 2: 响应时间过长

```
Average response time: 10000ms
```

**可能原因**:
- LLM API 响应慢
- 数据库查询慢
- 资源不足

**解决方案**:
1. 检查 LLM API 状态
2. 优化数据库查询
3. 增加服务器资源

### 问题 3: 高失败率

```
Success rate: 50%
```

**可能原因**:
- API 限流
- 资源耗尽
- 配置错误

**解决方案**:
1. 检查日志文件
2. 增加超时设置
3. 验证配置

## 最佳实践

1. **逐步增加负载**: 从少量用户开始，逐步增加
2. **监控系统资源**: 使用 `htop`、`nvidia-smi` 等工具
3. **记录基准**: 保存每次测试结果作为对比
4. **隔离测试环境**: 避免其他进程干扰
5. **多次测试**: 运行多次取平均值

## 进阶使用

### 自定义测试场景

编辑 `locustfile.py` 添加新的任务：

```python
@task(2)
def custom_task(self):
    """自定义任务"""
    # 你的测试逻辑
    pass
```

### 分布式测试

在多台机器上运行 Locust：

```bash
# Master 节点
locust -f locustfile.py --master

# Worker 节点
locust -f locustfile.py --worker --master-host=<master-ip>
```

### 持续集成

将性能测试集成到 CI/CD：

```yaml
# .github/workflows/performance.yml
- name: Run performance tests
  run: |
    locust -f tests/e2e/performance/locustfile.py \
      --headless \
      --users=10 \
      --spawn-rate=2 \
      --run-time=60s
```

## 参考资料

- [Locust 官方文档](https://docs.locust.io/)
- [FastAPI 性能优化](https://fastapi.tiangolo.com/deployment/concepts/)
- [Python 异步编程](https://docs.python.org/3/library/asyncio.html)
