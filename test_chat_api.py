"""
简单的 API 测试脚本

测试 LangGraph 对话功能
"""

import asyncio

import httpx


async def test_chat_api():
    """测试对话 API"""
    base_url = "http://localhost:8000"

    async with httpx.AsyncClient() as client:
        print("=" * 60)
        print("测试 LangGraph 对话 API")
        print("=" * 60)

        # 测试 1: 创建新会话并发送消息
        print("\n1. 测试创建新会话并发送消息...")
        chat_request = {"message": "你好，请介绍一下你自己", "user_id": 1, "metadata": {"test": True}}

        response = await client.post(f"{base_url}/api/v1/chat", json=chat_request)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Thread ID: {data['thread_id']}")
            print(f"响应: {data['response']}")
            print(f"耗时: {data['duration_ms']}ms")
            thread_id = data["thread_id"]
        else:
            print(f"错误: {response.text}")
            return

        # 测试 2: 在同一会话中继续对话
        print("\n2. 测试在同一会话中继续对话...")
        chat_request2 = {"message": "你能做什么？", "user_id": 1, "thread_id": thread_id}

        response = await client.post(f"{base_url}/api/v1/chat", json=chat_request2)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {data['response']}")
            print(f"耗时: {data['duration_ms']}ms")

        # 测试 3: 获取会话列表
        print("\n3. 测试获取会话列表...")
        response = await client.get(f"{base_url}/api/v1/conversations", params={"user_id": 1})
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            conversations = response.json()
            print(f"会话数量: {len(conversations)}")
            if conversations:
                print(f"第一个会话: {conversations[0]['title']}")
                print(f"消息数量: {conversations[0]['message_count']}")

        # 测试 4: 获取会话详情
        print("\n4. 测试获取会话详情...")
        response = await client.get(f"{base_url}/api/v1/conversations/{thread_id}")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            detail = response.json()
            print(f"会话标题: {detail['conversation']['title']}")
            print(f"消息数量: {len(detail['messages'])}")
            for i, msg in enumerate(detail["messages"], 1):
                print(f"  消息 {i} ({msg['role']}): {msg['content'][:50]}...")

        # 测试 5: 获取会话消息历史
        print("\n5. 测试获取消息历史...")
        response = await client.get(f"{base_url}/api/v1/conversations/{thread_id}/messages")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            messages = response.json()
            print(f"消息数量: {len(messages)}")

        # 测试 6: 获取会话状态
        print("\n6. 测试获取会话状态...")
        response = await client.get(f"{base_url}/api/v1/conversations/{thread_id}/state")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            state = response.json()
            print(f"状态: {state.get('values', {})}")

        # 测试 7: 更新会话标题
        print("\n7. 测试更新会话标题...")
        update_data = {"title": "测试会话 - 已更新"}
        response = await client.patch(f"{base_url}/api/v1/conversations/{thread_id}", json=update_data)
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            print(f"更新成功: {response.json()}")

        # 测试 8: 导出会话
        print("\n8. 测试导出会话...")
        response = await client.get(f"{base_url}/api/v1/conversations/{thread_id}/export")
        print(f"状态码: {response.status_code}")
        if response.status_code == 200:
            export_data = response.json()
            print(f"导出成功，包含 {len(export_data['messages'])} 条消息")

        print("\n" + "=" * 60)
        print("所有测试完成!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_chat_api())
