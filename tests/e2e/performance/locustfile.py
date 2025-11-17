"""
Locust 性能测试 - 并发聊天测试

测试 5 个用户同时进行 chat，分析性能瓶颈
"""

import random
import time

from locust import HttpUser, between, events, task


class ChatUser(HttpUser):
    """模拟聊天用户"""

    wait_time = between(1, 3)  # 每个请求之间等待 1-3 秒
    token = None
    thread_id = None

    def on_start(self):
        """用户启动时执行：注册并登录"""
        # 生成唯一的用户名
        username = f"perf_user_{random.randint(10000, 99999)}_{int(time.time())}"
        password = "Test@123456"

        # 注册用户
        register_response = self.client.post(
            "/api/v1/auth/register",
            json={
                "username": username,
                "password": password,
                "email": f"{username}@test.com",
                "nickname": username,
            },
            name="注册用户",
        )

        if register_response.status_code not in [200, 201]:
            print(f"❌ 用户 {username} 注册失败: HTTP {register_response.status_code}")
            return

        # 登录获取 token
        login_response = self.client.post(
            "/api/v1/auth/login",
            params={"username": username, "password": password},
            name="用户登录",
        )

        if login_response.status_code == 200:
            result = login_response.json()
            if result.get("success"):
                self.token = result["data"]["access_token"]
                print(f"✅ 用户 {username} 登录成功")
            else:
                print(f"❌ 用户 {username} 登录失败: {result.get('msg')}")
        else:
            print(f"❌ 用户 {username} 登录失败: HTTP {login_response.status_code}")

    @task(3)
    def send_chat_message(self):
        """发送聊天消息（权重 3）"""
        if not self.token:
            return

        messages = [
            "你好，请介绍一下你自己",
            "今天天气怎么样？",
            "请帮我写一段 Python 代码",
            "什么是机器学习？",
            "推荐几本好书",
            "1+1等于几？",
            "请解释一下什么是 FastAPI",
            "如何提高代码质量？",
        ]

        message = random.choice(messages)

        headers = {"Authorization": f"Bearer {self.token}"}

        start_time = time.time()

        response = self.client.post(
            "/api/v1/chat",
            json={"message": message, "thread_id": self.thread_id},
            headers=headers,
            name="发送聊天消息",
        )

        duration = (time.time() - start_time) * 1000  # 转换为毫秒

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                self.thread_id = result["data"]["thread_id"]
                response_text = result["data"]["response"]
                print(f"✅ 聊天成功 ({duration:.0f}ms): {response_text[:50]}...")
            else:
                print(f"❌ 聊天失败: {result.get('msg')}")
        else:
            print(f"❌ 聊天失败: HTTP {response.status_code}")

    @task(1)
    def get_conversations(self):
        """获取会话列表（权重 1）"""
        if not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        response = self.client.get(
            "/api/v1/conversations",
            headers=headers,
            name="获取会话列表",
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                total = result["data"]["total"]
                print(f"✅ 获取会话列表成功: {total} 个会话")
        else:
            print(f"❌ 获取会话列表失败: HTTP {response.status_code}")

    @task(1)
    def get_user_settings(self):
        """获取用户设置（权重 1）"""
        if not self.token:
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        response = self.client.get(
            "/api/v1/users/settings",
            headers=headers,
            name="获取用户设置",
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                print("✅ 获取用户设置成功")
        else:
            print(f"❌ 获取用户设置失败: HTTP {response.status_code}")


# 性能测试事件钩子
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时执行"""
    print("\n" + "=" * 60)
    print("🚀 性能测试开始")
    print(f"目标地址: {environment.host}")
    print(
        f"并发用户数: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}"
    )
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时执行"""
    print("\n" + "=" * 60)
    print("🏁 性能测试结束")
    print("=" * 60 + "\n")

    # 打印统计信息
    stats = environment.stats
    print("\n📊 性能统计摘要:")
    print("-" * 60)

    for name, stat in stats.entries.items():
        if stat.num_requests > 0:
            print(f"\n接口: {name}")
            print(f"  请求总数: {stat.num_requests}")
            print(f"  失败数: {stat.num_failures}")
            print(f"  成功率: {(1 - stat.num_failures / stat.num_requests) * 100:.2f}%")
            print(f"  平均响应时间: {stat.avg_response_time:.2f}ms")
            print(f"  中位数响应时间: {stat.median_response_time:.2f}ms")
            print(f"  95% 响应时间: {stat.get_response_time_percentile(0.95):.2f}ms")
            print(f"  99% 响应时间: {stat.get_response_time_percentile(0.99):.2f}ms")
            print(f"  最小响应时间: {stat.min_response_time:.2f}ms")
            print(f"  最大响应时间: {stat.max_response_time:.2f}ms")
            print(f"  RPS: {stat.total_rps:.2f}")

    print("\n" + "-" * 60)
    print(f"总请求数: {stats.total.num_requests}")
    print(f"总失败数: {stats.total.num_failures}")
    print(f"总体成功率: {(1 - stats.total.num_failures / stats.total.num_requests) * 100:.2f}%")
    print(f"总体平均响应时间: {stats.total.avg_response_time:.2f}ms")
    print(f"总体 RPS: {stats.total.total_rps:.2f}")
    print("=" * 60 + "\n")


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """每个请求完成时执行"""
    if exception:
        print(f"❌ 请求失败: {name} - {exception}")
