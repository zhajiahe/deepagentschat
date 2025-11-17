"""
性能分析脚本

分析 Locust 测试结果，识别性能瓶颈
"""

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []

    def register_and_login(self, user_id: int) -> tuple[str, str]:
        """注册并登录用户"""
        username = f"perf_user_{user_id}_{int(time.time())}"
        password = "Test@123456"

        # 注册
        register_response = httpx.post(
            f"{self.base_url}/api/v1/auth/register",
            json={
                "username": username,
                "password": password,
                "email": f"{username}@test.com",
                "nickname": username,
            },
            timeout=30.0,
        )

        if register_response.status_code not in [200, 201]:
            print(f"  ❌ 注册失败: HTTP {register_response.status_code}")
            return None, None

        # 登录获取 token
        login_response = httpx.post(
            f"{self.base_url}/api/v1/auth/login",
            params={"username": username, "password": password},
            timeout=30.0,
        )

        if login_response.status_code == 200:
            result = login_response.json()
            if result.get("success"):
                return result["data"]["access_token"], username

        print(f"  ❌ 登录失败: HTTP {login_response.status_code}")
        return None, None

    def send_chat_message(self, token: str, message: str, thread_id: str = None) -> dict:
        """发送聊天消息并测量性能"""
        start_time = time.time()

        try:
            response = httpx.post(
                f"{self.base_url}/api/v1/chat",
                json={"message": message, "thread_id": thread_id},
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0,
            )

            duration = (time.time() - start_time) * 1000

            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "duration": duration,
                    "thread_id": result["data"]["thread_id"],
                    "response_length": len(result["data"]["response"]),
                }
            else:
                return {
                    "success": False,
                    "duration": duration,
                    "error": f"HTTP {response.status_code}",
                }
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return {"success": False, "duration": duration, "error": str(e)}

    def simulate_user(self, user_id: int, num_messages: int = 5) -> dict:
        """模拟单个用户的完整流程"""
        print(f"👤 用户 {user_id} 开始测试...")

        # 注册登录
        token, username = self.register_and_login(user_id)
        if not token:
            print(f"❌ 用户 {user_id} 注册失败")
            return {"user_id": user_id, "success": False, "error": "注册失败"}

        print(f"✅ 用户 {user_id} ({username}) 注册成功")

        # 发送多条消息
        messages = [
            "你好，请介绍一下你自己",
            "今天天气怎么样？",
            "1+1等于几？",
            "请解释一下什么是 FastAPI",
            "推荐几本好书",
        ]

        thread_id = None
        durations = []
        errors = []

        for i, message in enumerate(messages[:num_messages]):
            print(f"  📨 用户 {user_id} 发送消息 {i+1}/{num_messages}: {message[:30]}...")

            result = self.send_chat_message(token, message, thread_id)

            if result["success"]:
                thread_id = result["thread_id"]
                durations.append(result["duration"])
                print(f"  ✅ 响应时间: {result['duration']:.0f}ms")
            else:
                errors.append(result["error"])
                print(f"  ❌ 失败: {result['error']}")

            # 模拟用户思考时间
            time.sleep(0.5)

        return {
            "user_id": user_id,
            "username": username,
            "success": True,
            "total_messages": num_messages,
            "successful_messages": len(durations),
            "failed_messages": len(errors),
            "durations": durations,
            "errors": errors,
            "avg_duration": statistics.mean(durations) if durations else 0,
            "min_duration": min(durations) if durations else 0,
            "max_duration": max(durations) if durations else 0,
        }

    def run_concurrent_test(self, num_users: int = 5, messages_per_user: int = 5):
        """运行并发测试"""
        print("\n" + "=" * 70)
        print("🚀 开始并发性能测试")
        print(f"   并发用户数: {num_users}")
        print(f"   每用户消息数: {messages_per_user}")
        print("=" * 70 + "\n")

        start_time = time.time()

        # 使用线程池并发执行
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(self.simulate_user, i, messages_per_user) for i in range(num_users)]

            for future in as_completed(futures):
                try:
                    result = future.result()
                    self.results.append(result)
                except Exception as e:
                    print(f"❌ 用户测试异常: {e}")

        total_duration = time.time() - start_time

        print("\n" + "=" * 70)
        print(f"✅ 测试完成，总耗时: {total_duration:.2f}秒")
        print("=" * 70 + "\n")

        self.analyze_results(total_duration)

    def analyze_results(self, total_duration: float):
        """分析测试结果"""
        print("\n📊 性能分析报告")
        print("=" * 70)

        # 统计成功/失败
        successful_users = [r for r in self.results if r.get("success")]
        failed_users = [r for r in self.results if not r.get("success")]

        print("\n1. 用户统计:")
        print(f"   总用户数: {len(self.results)}")
        print(f"   成功用户: {len(successful_users)}")
        print(f"   失败用户: {len(failed_users)}")

        if not successful_users:
            print("\n❌ 没有成功的测试，无法分析性能")
            return

        # 统计消息
        total_messages = sum(r["total_messages"] for r in successful_users)
        successful_messages = sum(r["successful_messages"] for r in successful_users)
        failed_messages = sum(r["failed_messages"] for r in successful_users)

        print("\n2. 消息统计:")
        print(f"   总消息数: {total_messages}")
        print(f"   成功消息: {successful_messages}")
        print(f"   失败消息: {failed_messages}")
        print(f"   成功率: {(successful_messages / total_messages * 100):.2f}%")

        # 响应时间分析
        all_durations = []
        for r in successful_users:
            all_durations.extend(r["durations"])

        if all_durations:
            print("\n3. 响应时间分析:")
            print(f"   平均响应时间: {statistics.mean(all_durations):.2f}ms")
            print(f"   中位数响应时间: {statistics.median(all_durations):.2f}ms")
            print(f"   最小响应时间: {min(all_durations):.2f}ms")
            print(f"   最大响应时间: {max(all_durations):.2f}ms")
            print(f"   标准差: {statistics.stdev(all_durations):.2f}ms")

            # 计算百分位数
            sorted_durations = sorted(all_durations)
            p50 = sorted_durations[int(len(sorted_durations) * 0.50)]
            p90 = sorted_durations[int(len(sorted_durations) * 0.90)]
            p95 = sorted_durations[int(len(sorted_durations) * 0.95)]
            p99 = sorted_durations[int(len(sorted_durations) * 0.99)]

            print(f"   P50 (中位数): {p50:.2f}ms")
            print(f"   P90: {p90:.2f}ms")
            print(f"   P95: {p95:.2f}ms")
            print(f"   P99: {p99:.2f}ms")

        # 吞吐量分析
        print("\n4. 吞吐量分析:")
        print(f"   总耗时: {total_duration:.2f}秒")
        print(f"   平均 RPS (请求/秒): {successful_messages / total_duration:.2f}")
        print(f"   平均每用户耗时: {total_duration / len(successful_users):.2f}秒")

        # 性能瓶颈识别
        print("\n5. 性能瓶颈分析:")

        avg_duration = statistics.mean(all_durations) if all_durations else 0

        if avg_duration > 5000:
            print("   ⚠️  严重瓶颈: 平均响应时间超过 5 秒")
            print("      建议:")
            print("      - 检查 LLM API 响应速度")
            print("      - 考虑增加超时设置")
            print("      - 优化数据库查询")
        elif avg_duration > 2000:
            print("   ⚠️  中等瓶颈: 平均响应时间超过 2 秒")
            print("      建议:")
            print("      - 检查 LLM API 性能")
            print("      - 考虑使用缓存")
        elif avg_duration > 1000:
            print("   ℹ️  轻微瓶颈: 平均响应时间超过 1 秒")
            print("      建议:")
            print("      - 监控 LLM API 响应时间")
        else:
            print("   ✅ 性能良好: 平均响应时间在 1 秒以内")

        # 并发性能
        if len(successful_users) >= 5:
            concurrent_efficiency = (successful_messages / total_duration) / len(successful_users)
            print("\n6. 并发效率:")
            print(f"   每用户平均 RPS: {concurrent_efficiency:.2f}")

            if concurrent_efficiency < 0.5:
                print("   ⚠️  并发效率较低，可能存在资源竞争")
                print("      建议:")
                print("      - 检查数据库连接池大小")
                print("      - 检查是否有锁竞争")
                print("      - 考虑使用异步处理")
            else:
                print("   ✅ 并发效率良好")

        # 错误分析
        all_errors = []
        for r in successful_users:
            all_errors.extend(r["errors"])

        if all_errors:
            print("\n7. 错误分析:")
            print(f"   错误总数: {len(all_errors)}")
            error_types = {}
            for error in all_errors:
                error_types[error] = error_types.get(error, 0) + 1

            print("   错误类型分布:")
            for error, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                print(f"      - {error}: {count} 次")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    analyzer = PerformanceAnalyzer()
    analyzer.run_concurrent_test(num_users=5, messages_per_user=5)
