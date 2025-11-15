"""
对话接口性能测试

使用 Locust 进行对话 API 的负载测试
模拟 1/5/10 个用户并发访问时的性能表现
"""

import os
import time

import gevent
from locust import HttpUser, between, events, task
from locust.env import Environment
from locust.stats import print_stats


class ChatUser(HttpUser):
    """对话用户类"""

    # 用户操作间隔：1-3秒
    wait_time = between(1, 3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = None
        self.thread_id = None
        self.base_url = os.getenv("PERF_TEST_BASE_URL", "http://localhost:8000")

    def on_start(self):
        """用户启动时执行：登录并创建会话"""
        try:
            # 登录获取token
            login_response = self.client.post(f"{self.base_url}/api/v1/auth/login?username=admin&password=admin123")

            if login_response.status_code == 200:
                login_data = login_response.json()
                if login_data.get("success") and "data" in login_data:
                    self.token = login_data["data"]["access_token"]
                    print(f"用户登录成功，token: {self.token[:20]}...")

                    # 创建会话
                    headers = {"Authorization": f"Bearer {self.token}"}
                    conversation_response = self.client.post(
                        f"{self.base_url}/api/v1/conversations",
                        json={"title": f"性能测试会话-{time.time()}"},
                        headers=headers,
                    )

                    if conversation_response.status_code == 200:
                        response_data = conversation_response.json()
                        if response_data.get("success") and "data" in response_data:
                            self.thread_id = response_data["data"]["thread_id"]
                            print(f"会话创建成功，thread_id: {self.thread_id}")
                        else:
                            print(f"会话创建响应格式错误: {response_data}")
                    else:
                        print(f"会话创建失败: {conversation_response.status_code} - {conversation_response.text}")
                else:
                    print(f"登录响应格式错误: {login_data}")
            else:
                print(f"登录失败: {login_response.status_code} - {login_response.text}")

        except Exception as e:
            print(f"用户初始化失败: {e}")

    @task(3)  # 权重3，非流式对话更常用
    def chat_non_stream(self):
        """非流式对话任务"""
        if not self.token or not self.thread_id:
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        # 发送对话请求
        chat_request = {
            "thread_id": self.thread_id,
            "message": f"你好，这是一条性能测试消息 - {time.time()}",
            "stream": False,
        }

        with self.client.post(
            f"{self.base_url}/api/v1/chat", json=chat_request, headers=headers, catch_response=True
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                # 检查是否是成功的响应
                if (
                    isinstance(response_data, dict)
                    and response_data.get("success")
                    and "data" in response_data
                    and "response" in response_data["data"]
                ):
                    response.success()
                    chat_data = response_data["data"]
                    print(f"非流式对话成功: {len(chat_data.get('response', ''))} 字符")
                else:
                    response.failure(f"API返回错误: {response_data}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")

    @task(2)  # 权重2，流式对话
    def chat_stream(self):
        """流式对话任务"""
        if not self.token or not self.thread_id:
            return

        headers = {"Authorization": f"Bearer {self.token}", "Accept": "text/event-stream"}

        chat_request = {
            "thread_id": self.thread_id,
            "message": f"请用流式响应回复这条性能测试消息 - {time.time()}",
            "stream": True,
        }

        with self.client.post(
            f"{self.base_url}/api/v1/chat/stream", json=chat_request, headers=headers, catch_response=True
        ) as response:
            if response.status_code == 200:
                # 对于流式响应，我们简单检查响应是否成功开始
                response.success()
                print("流式对话开始成功")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")

    @task(1)  # 权重1，偶尔停止对话
    def stop_chat(self):
        """停止对话任务"""
        if not self.token or not self.thread_id:
            return

        headers = {"Authorization": f"Bearer {self.token}"}

        stop_request = {"thread_id": self.thread_id}

        with self.client.post(
            f"{self.base_url}/api/v1/chat/stop", json=stop_request, headers=headers, catch_response=True
        ) as response:
            if response.status_code == 200:
                response_data = response.json()
                # 检查响应格式
                if isinstance(response_data, dict) and response_data.get("success") and "data" in response_data:
                    stop_data = response_data["data"]
                    if "status" in stop_data:
                        if stop_data["status"] == "stopped":
                            response.success()
                            print("停止对话成功")
                        elif stop_data["status"] == "not_running":
                            # 没有运行中的任务，这不是错误
                            response.success()
                            print("没有运行中的对话，无需停止")
                        else:
                            response.failure(f"未知状态: {stop_data}")
                    else:
                        response.failure(f"响应数据中缺少status字段: {stop_data}")
                else:
                    response.failure(f"API响应格式错误: {response_data}")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时的回调"""
    print("=" * 50)
    print("🚀 开始对话接口性能测试")
    print(f"目标URL: {os.getenv('PERF_TEST_BASE_URL', 'http://localhost:8000')}")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时的回调"""
    print("=" * 50)
    print("✅ 对话接口性能测试完成")
    print("=" * 50)
    print_stats(environment.stats)


def run_performance_test(users: int = 1, spawn_rate: float = 1.0, run_time: str = "1m"):
    """
    运行性能测试

    Args:
        users: 用户数量
        spawn_rate: 用户生成速率 (users/second)
        run_time: 运行时间 (e.g., "30s", "5m", "1h")
    """
    # 设置环境变量
    os.environ.setdefault("PERF_TEST_BASE_URL", "http://localhost:8000")

    # 创建Locust环境
    env = Environment(user_classes=[ChatUser])

    # 配置运行参数
    env.create_local_runner()

    # 开始测试
    env.runner.start(users, spawn_rate=spawn_rate)

    # 运行指定时间
    print(f"🎯 启动 {users} 个并发用户，生成速率: {spawn_rate} users/s，运行时间: {run_time}")
    gevent.sleep(parse_time(run_time))

    # 停止测试
    env.runner.stop()

    # 等待统计完成
    gevent.sleep(2)


def parse_time(time_str: str) -> int:
    """解析时间字符串为秒数"""
    time_str = time_str.lower()
    if time_str.endswith("s"):
        return int(time_str[:-1])
    elif time_str.endswith("m"):
        return int(time_str[:-1]) * 60
    elif time_str.endswith("h"):
        return int(time_str[:-1]) * 3600
    else:
        return int(time_str)


if __name__ == "__main__":
    """直接运行性能测试"""
    import argparse

    parser = argparse.ArgumentParser(description="对话接口性能测试")
    parser.add_argument("--users", type=int, default=1, help="并发用户数 (默认: 1)")
    parser.add_argument("--spawn-rate", type=float, default=1.0, help="用户生成速率 users/s (默认: 1.0)")
    parser.add_argument("--run-time", type=str, default="30s", help="运行时间 (默认: 30s)")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000", help="API基础URL")

    args = parser.parse_args()

    # 设置环境变量
    os.environ["PERF_TEST_BASE_URL"] = args.base_url

    # 运行测试
    run_performance_test(users=args.users, spawn_rate=args.spawn_rate, run_time=args.run_time)
