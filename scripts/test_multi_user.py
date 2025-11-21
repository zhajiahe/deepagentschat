#!/usr/bin/env python3
"""
多用户并发测试脚本
测试多个用户同时上传文件、查询文件、与 Agent 对话的场景
"""

import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

API_BASE = "http://localhost:8000/api/v1"


class UserSession:
    """用户会话类"""

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.token = None
        self.user_id = None
        self.thread_id = None
        self.uploaded_files = []

    def login(self) -> bool:
        """登录"""
        try:
            response = requests.post(
                f"{API_BASE}/auth/login", params={"username": self.username, "password": self.password}
            )

            if response.status_code != 200:
                print(f"❌ [{self.username}] 登录失败: {response.status_code}")
                return False

            data = response.json()
            self.token = data["data"]["access_token"]
            self.user_id = data["data"]["id"]
            print(f"✅ [{self.username}] 登录成功: user_id={self.user_id}")
            return True
        except Exception as e:
            print(f"❌ [{self.username}] 登录异常: {e}")
            return False

    def upload_file(self, filename: str, content: str) -> bool:
        """上传文件"""
        try:
            files = {"file": (filename, content, "text/plain")}
            response = requests.post(
                f"{API_BASE}/files/upload", headers={"Authorization": f"Bearer {self.token}"}, files=files
            )

            if response.status_code != 200:
                print(f"❌ [{self.username}] 上传文件 {filename} 失败: {response.status_code}")
                return False

            self.uploaded_files.append(filename)
            print(f"✅ [{self.username}] 上传文件成功: {filename}")
            return True
        except Exception as e:
            print(f"❌ [{self.username}] 上传文件异常: {e}")
            return False

    def list_files(self) -> list[str]:
        """列出文件"""
        try:
            response = requests.get(f"{API_BASE}/files/list", headers={"Authorization": f"Bearer {self.token}"})

            if response.status_code != 200:
                print(f"❌ [{self.username}] 获取文件列表失败: {response.status_code}")
                return []

            data = response.json()
            files = data.get("data", {}).get("files", [])
            # 文件对象有 filename 字段，不是 name
            print(f"📁 [{self.username}] 文件列表 ({len(files)} 个): {[f['filename'] for f in files]}")
            return [f["filename"] for f in files]
        except Exception as e:
            print(f"❌ [{self.username}] 获取文件列表异常: {e}")
            return []

    def create_conversation(self) -> bool:
        """创建对话"""
        try:
            response = requests.post(
                f"{API_BASE}/conversations",
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                json={"title": f"{self.username} 的测试对话"},
            )

            if response.status_code != 200:
                print(f"❌ [{self.username}] 创建对话失败: {response.status_code}")
                return False

            self.thread_id = response.json()["data"]["thread_id"]
            print(f"✅ [{self.username}] 创建对话成功: {self.thread_id}")
            return True
        except Exception as e:
            print(f"❌ [{self.username}] 创建对话异常: {e}")
            return False

    def chat(self, message: str, print_full_response: bool = False) -> str:
        """发送聊天消息"""
        try:
            print(f"\n💬 [{self.username}] 发送消息: {message}")

            response = requests.post(
                f"{API_BASE}/chat",
                headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                json={"thread_id": self.thread_id, "message": message},
            )

            if response.status_code != 200:
                print(f"❌ [{self.username}] 发送消息失败: {response.status_code}")
                return ""

            data = response.json()
            reply = data["data"]["response"]

            if print_full_response:
                print(f"\n{'='*60}")
                print(f"🤖 [{self.username}] Agent 完整回复:")
                print(f"{'-'*60}")
                print(reply)
                print(f"{'='*60}\n")
            else:
                # 截取前200个字符
                preview = reply[:200] + "..." if len(reply) > 200 else reply
                print(f"🤖 [{self.username}] Agent 回复预览: {preview}")

            return reply
        except Exception as e:
            print(f"❌ [{self.username}] 发送消息异常: {e}")
            return ""


def test_user_workflow(username: str, password: str, user_index: int) -> dict:
    """测试单个用户的完整工作流"""
    print(f"\n{'='*60}")
    print(f"开始测试用户 #{user_index}: {username}")
    print(f"{'='*60}")

    results = {
        "username": username,
        "login": False,
        "upload": False,
        "list_files": False,
        "conversation": False,
        "chat_list": False,
        "chat_read": False,
        "chat_analyze": False,
        "errors": [],
    }

    session = UserSession(username, password)

    # 1. 登录
    if not session.login():
        results["errors"].append("登录失败")
        return results
    results["login"] = True
    time.sleep(0.5)

    # 2. 上传文件
    file_content = f"""# {username} 的测试数据
时间戳: {time.time()}
随机数: {random.randint(1000, 9999)}

这是用户 {username} 上传的测试文件。
包含一些测试数据供 Agent 分析。

数据行:
- 项目1: 值 {random.randint(100, 200)}
- 项目2: 值 {random.randint(200, 300)}
- 项目3: 值 {random.randint(300, 400)}
"""

    filename = f"test_{username}_{int(time.time())}.txt"
    if not session.upload_file(filename, file_content):
        results["errors"].append("上传文件失败")
        return results
    results["upload"] = True
    time.sleep(0.5)

    # 3. 列出文件
    files = session.list_files()
    if filename not in files:
        results["errors"].append(f"上传的文件 {filename} 未在文件列表中")
    else:
        results["list_files"] = True
    time.sleep(0.5)

    # 4. 创建对话
    if not session.create_conversation():
        results["errors"].append("创建对话失败")
        return results
    results["conversation"] = True
    time.sleep(0.5)

    # 5. 测试对话 - 列出文件
    reply = session.chat("请列出 /mnt/data 目录的所有文件", print_full_response=True)
    if filename in reply:
        results["chat_list"] = True
        print(f"✅ [{username}] Agent 能看到上传的文件 {filename}")
    else:
        results["errors"].append(f"Agent 回复中未找到文件 {filename}")
        print(f"❌ [{username}] Agent 看不到上传的文件 {filename}")
    time.sleep(1)

    # 6. 测试对话 - 读取文件
    reply = session.chat(f"请读取文件 /mnt/data/{filename} 的内容", print_full_response=True)
    if username in reply or "项目1" in reply:
        results["chat_read"] = True
        print(f"✅ [{username}] Agent 能读取文件内容")
    else:
        results["errors"].append("Agent 无法读取文件内容")
        print(f"❌ [{username}] Agent 无法读取文件内容")
    time.sleep(1)

    # 7. 测试对话 - 分析文件
    reply = session.chat(f"请分析文件 {filename} 中的数据，统计项目数量", print_full_response=True)
    if "3" in reply or "三" in reply or "项目" in reply:
        results["chat_analyze"] = True
        print(f"✅ [{username}] Agent 能分析文件")
    else:
        results["errors"].append("Agent 无法分析文件")
        print(f"❌ [{username}] Agent 无法分析文件")

    return results


def main():
    """主测试函数"""
    print("=" * 60)
    print("多用户并发测试开始")
    print("=" * 60)

    # 测试用户列表（使用同一个账号模拟多个并发会话）
    test_users = [
        ("huaao", "huaao123"),
        ("huaao", "huaao123"),
        ("huaao", "huaao123"),
    ]

    start_time = time.time()

    # 方案1: 顺序执行（便于调试）
    print("\n【方案1: 顺序执行】")
    results_sequential = []
    for i, (username, password) in enumerate(test_users, 1):
        result = test_user_workflow(username, password, i)
        results_sequential.append(result)
        time.sleep(2)  # 用户之间间隔2秒

    # 方案2: 并发执行（测试并发性能）
    print("\n\n【方案2: 并发执行】")
    with ThreadPoolExecutor(max_workers=len(test_users)) as executor:
        futures = {
            executor.submit(test_user_workflow, username, password, i): (username, i)
            for i, (username, password) in enumerate(test_users, 1)
        }

        results_concurrent = []
        for future in as_completed(futures):
            username, index = futures[future]
            try:
                result = future.result()
                results_concurrent.append(result)
            except Exception as e:
                print(f"❌ 用户 {username} #{index} 执行异常: {e}")

    elapsed_time = time.time() - start_time

    # 输出测试报告
    print("\n\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)

    print(f"\n总耗时: {elapsed_time:.2f} 秒")
    print(f"测试用户数: {len(test_users)}")

    # 顺序执行结果
    print("\n【顺序执行结果】")
    success_count = 0
    for i, result in enumerate(results_sequential, 1):
        all_passed = all(
            [
                result["login"],
                result["upload"],
                result["list_files"],
                result["conversation"],
                result["chat_list"],
                result["chat_read"],
                result["chat_analyze"],
            ]
        )

        if all_passed:
            success_count += 1
            print(f"✅ 用户 #{i} ({result['username']}): 全部通过")
        else:
            print(f"❌ 用户 #{i} ({result['username']}): 部分失败")
            for error in result["errors"]:
                print(f"   - {error}")

    print(f"\n成功率: {success_count}/{len(test_users)} ({success_count/len(test_users)*100:.1f}%)")

    # 并发执行结果
    print("\n【并发执行结果】")
    success_count = 0
    for i, result in enumerate(results_concurrent, 1):
        all_passed = all(
            [
                result["login"],
                result["upload"],
                result["list_files"],
                result["conversation"],
                result["chat_list"],
                result["chat_read"],
                result["chat_analyze"],
            ]
        )

        if all_passed:
            success_count += 1
            print(f"✅ 用户 #{i} ({result['username']}): 全部通过")
        else:
            print(f"❌ 用户 #{i} ({result['username']}): 部分失败")
            for error in result["errors"]:
                print(f"   - {error}")

    print(f"\n成功率: {success_count}/{len(test_users)} ({success_count/len(test_users)*100:.1f}%)")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
