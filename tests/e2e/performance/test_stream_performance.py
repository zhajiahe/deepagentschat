"""
流式接口性能测试

测试 SSE 流式聊天接口的性能
"""

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


class StreamPerformanceAnalyzer:
    """流式接口性能分析器"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = []

    def register_and_login(self, user_id: int) -> tuple[str, str]:
        """注册并登录用户"""
        username = f"stream_user_{user_id}_{int(time.time())}"
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

    def send_stream_message(self, token: str, message: str, thread_id: str = None) -> dict:
        """发送流式聊天消息并测量性能"""
        start_time = time.time()
        first_chunk_time = None
        chunks_received = 0
        total_content = ""

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/api/v1/chat/stream",
                json={"message": message, "thread_id": thread_id},
                headers={"Authorization": f"Bearer {token}"},
                timeout=60.0,
            ) as response:
                if response.status_code != 200:
                    duration = (time.time() - start_time) * 1000
                    return {
                        "success": False,
                        "duration": duration,
                        "error": f"HTTP {response.status_code}",
                    }

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue

                    # 记录第一个 chunk 的时间
                    if first_chunk_time is None:
                        first_chunk_time = time.time()

                    chunks_received += 1

                    # 解析 SSE 数据
                    try:
                        import json

                        data = json.loads(line[6:])  # 去掉 "data: " 前缀

                        if data.get("type") == "content":
                            total_content += data.get("content", "")
                        elif data.get("done"):
                            break
                        elif data.get("stopped"):
                            break
                    except Exception:
                        pass

            total_duration = (time.time() - start_time) * 1000
            first_chunk_duration = (first_chunk_time - start_time) * 1000 if first_chunk_time else 0

            return {
                "success": True,
                "total_duration": total_duration,
                "first_chunk_duration": first_chunk_duration,
                "chunks_received": chunks_received,
                "content_length": len(total_content),
                "thread_id": None,  # 从响应中提取
            }

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return {"success": False, "duration": duration, "error": str(e)}

    def simulate_user(self, user_id: int, num_messages: int = 5) -> dict:
        """模拟单个用户的流式聊天"""
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
        results = []
        errors = []

        for i, message in enumerate(messages[:num_messages]):
            print(f"  📨 用户 {user_id} 发送消息 {i+1}/{num_messages}: {message[:30]}...")

            result = self.send_stream_message(token, message, thread_id)

            if result["success"]:
                thread_id = result.get("thread_id")
                results.append(result)
                print(
                    f"  ✅ 总耗时: {result['total_duration']:.0f}ms, "
                    f"首字节: {result['first_chunk_duration']:.0f}ms, "
                    f"chunks: {result['chunks_received']}"
                )
            else:
                errors.append(result["error"])
                print(f"  ❌ 失败: {result['error']}")

            # 模拟用户思考时间
            time.sleep(0.5)

        # 计算统计数据
        if results:
            total_durations = [r["total_duration"] for r in results]
            first_chunk_durations = [r["first_chunk_duration"] for r in results]

            return {
                "user_id": user_id,
                "username": username,
                "success": True,
                "total_messages": num_messages,
                "successful_messages": len(results),
                "failed_messages": len(errors),
                "results": results,
                "errors": errors,
                "avg_total_duration": statistics.mean(total_durations),
                "avg_first_chunk_duration": statistics.mean(first_chunk_durations),
                "min_total_duration": min(total_durations),
                "max_total_duration": max(total_durations),
            }
        else:
            return {
                "user_id": user_id,
                "username": username,
                "success": False,
                "total_messages": num_messages,
                "successful_messages": 0,
                "failed_messages": len(errors),
                "errors": errors,
            }

    def run_concurrent_test(self, num_users: int = 5, messages_per_user: int = 5):
        """运行并发测试"""
        print("\n" + "=" * 70)
        print("🚀 开始流式接口并发性能测试")
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
        print("\n📊 流式接口性能分析报告")
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

        # 收集所有结果
        all_results = []
        for user in successful_users:
            all_results.extend(user.get("results", []))

        if not all_results:
            print("\n❌ 没有成功的消息，无法分析性能")
            return

        # 总响应时间分析
        total_durations = [r["total_duration"] for r in all_results]
        first_chunk_durations = [r["first_chunk_duration"] for r in all_results]
        chunks_counts = [r["chunks_received"] for r in all_results]

        print("\n3. 总响应时间分析:")
        print(f"   平均总响应时间: {statistics.mean(total_durations):.2f}ms")
        print(f"   中位数总响应时间: {statistics.median(total_durations):.2f}ms")
        print(f"   最小总响应时间: {min(total_durations):.2f}ms")
        print(f"   最大总响应时间: {max(total_durations):.2f}ms")
        print(f"   标准差: {statistics.stdev(total_durations):.2f}ms")

        # 首字节时间分析（TTFB - Time To First Byte）
        print("\n4. 首字节时间分析 (TTFB):")
        print(f"   平均首字节时间: {statistics.mean(first_chunk_durations):.2f}ms")
        print(f"   中位数首字节时间: {statistics.median(first_chunk_durations):.2f}ms")
        print(f"   最小首字节时间: {min(first_chunk_durations):.2f}ms")
        print(f"   最大首字节时间: {max(first_chunk_durations):.2f}ms")

        # 流式传输效率
        print("\n5. 流式传输分析:")
        print(f"   平均 chunks 数: {statistics.mean(chunks_counts):.2f}")
        print(f"   中位数 chunks 数: {statistics.median(chunks_counts):.0f}")

        # 计算流式传输的优势
        avg_total = statistics.mean(total_durations)
        avg_first_chunk = statistics.mean(first_chunk_durations)
        streaming_advantage = ((avg_total - avg_first_chunk) / avg_total) * 100

        print("\n   流式传输优势:")
        print(f"   - 用户等待时间减少: {streaming_advantage:.1f}%")
        print(f"   - 首字节后继续传输: {avg_total - avg_first_chunk:.0f}ms")

        # 吞吐量分析
        print("\n6. 吞吐量分析:")
        print(f"   总耗时: {total_duration:.2f}秒")
        print(f"   平均 RPS: {successful_messages / total_duration:.2f}")
        print(f"   平均每用户耗时: {total_duration / len(successful_users):.2f}秒")

        # 性能对比
        print("\n7. 与非流式接口对比:")
        print("   流式接口优势:")
        print(f"   ✅ 首字节时间: {statistics.mean(first_chunk_durations):.0f}ms (用户感知延迟)")
        print(f"   ℹ️  总响应时间: {statistics.mean(total_durations):.0f}ms (实际处理时间)")
        print("   ✅ 用户体验更好：边生成边显示，无需等待完整响应")

        # 性能瓶颈识别
        print("\n8. 性能瓶颈分析:")

        avg_first_chunk = statistics.mean(first_chunk_durations)

        if avg_first_chunk > 2000:
            print("   ⚠️  首字节延迟较高 (> 2s)")
            print("      建议:")
            print("      - 优化 LLM API 连接")
            print("      - 检查网络延迟")
            print("      - 优化数据库查询")
        elif avg_first_chunk > 1000:
            print("   ℹ️  首字节延迟适中 (1-2s)")
            print("      建议: 继续监控")
        else:
            print("   ✅ 首字节延迟良好 (< 1s)")

        print("\n" + "=" * 70)


if __name__ == "__main__":
    analyzer = StreamPerformanceAnalyzer()
    analyzer.run_concurrent_test(num_users=5, messages_per_user=5)
