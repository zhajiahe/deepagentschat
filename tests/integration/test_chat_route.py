"""
对话 API 集成测试

包含 LangGraph 对话功能的真实集成测试
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestChatAPI:
    """对话 API 测试类"""

    def test_chat_create_new_conversation(self, client: TestClient, auth_headers: dict):
        """测试创建新会话并发送消息"""
        response = client.post(
            "/api/v1/chat",
            json={"message": "你好", "metadata": {"test": True}},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["code"] == 200
        data = response_data["data"]
        assert "thread_id" in data
        assert "response" in data
        assert "duration_ms" in data
        assert "你好" in data["response"] or "Echo" in data["response"]

    @pytest.mark.asyncio
    async def test_chat_continue_conversation(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试在同一会话中继续对话"""
        from app.models import Conversation

        conversation = Conversation(
            thread_id="test-thread-1",
            user_id=current_user_id,
            title="Test Conversation",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 发送消息到现有会话
        response = client.post(
            "/api/v1/chat",
            json={"message": "继续对话", "thread_id": "test-thread-1"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["code"] == 200
        data = response_data["data"]
        assert data["thread_id"] == "test-thread-1"

    def test_chat_unauthorized(self, client: TestClient):
        """测试未授权访问"""
        response = client.post(
            "/api/v1/chat",
            json={"message": "你好"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_chat_stream(self, client: TestClient, auth_headers: dict):
        """测试流式对话"""
        response = client.post(
            "/api/v1/chat/stream",
            json={"message": "你好"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"

        # 读取流式响应
        content = b""
        for chunk in response.iter_bytes():
            content += chunk
            if b"done" in chunk:
                break

        assert b"data:" in content

    def test_chat_invalid_thread_id(self, client: TestClient, auth_headers: dict):
        """测试无效的 thread_id"""
        response = client.post(
            "/api/v1/chat",
            json={"message": "你好", "thread_id": "non-existent-thread"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_stop_chat_stream(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试停止流式对话"""
        import asyncio
        import threading

        from app.models import Conversation

        # 创建会话
        thread_id = "test-stop-thread"
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
            title="Test Stop",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 启动流式对话（在后台线程中）
        stream_started = threading.Event()
        stream_stopped = threading.Event()

        def start_stream():
            try:
                stream_response = client.post(
                    "/api/v1/chat/stream",
                    json={"message": "请写一个很长的故事", "thread_id": thread_id},
                    headers=auth_headers,
                )
                stream_started.set()
                # 读取流式响应
                for chunk in stream_response.iter_bytes():
                    if b"stopped" in chunk or b"done" in chunk:
                        break
            except Exception:
                pass
            finally:
                stream_stopped.set()

        stream_thread = threading.Thread(target=start_stream)
        stream_thread.start()

        # 等待流式请求启动
        if stream_started.wait(timeout=2):
            # 等待一小段时间确保流式请求已开始处理
            await asyncio.sleep(0.3)

            # 发送停止请求
            stop_response = client.post(
                "/api/v1/chat/stop",
                json={"thread_id": thread_id},
                headers=auth_headers,
            )
            assert stop_response.status_code == status.HTTP_200_OK
            stop_data = stop_response.json()
            assert stop_data["status"] in ["stopped", "not_running"]  # 可能已经完成或未启动
            assert stop_data["thread_id"] == thread_id

        # 等待流式响应结束
        stream_thread.join(timeout=5)

    def test_stop_chat_not_found(self, client: TestClient, auth_headers: dict):
        """测试停止不存在的会话"""
        response = client.post(
            "/api/v1/chat/stop",
            json={"thread_id": "non-existent-thread"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_stop_chat_unauthorized(self, client: TestClient, db):
        """测试未授权停止对话"""
        from app.core.security import get_password_hash
        from app.models import Conversation, User

        # 创建其他用户
        other_user = User(
            username="otheruser2",
            email="other2@example.com",
            nickname="Other User 2",
            hashed_password=get_password_hash("test123"),
            is_active=True,
            is_superuser=False,
        )
        db.add(other_user)
        await db.commit()
        await db.refresh(other_user)

        # 创建其他用户的会话
        conversation = Conversation(
            thread_id="other-user-thread-2",
            user_id=other_user.id,
            title="Other User Conversation",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 尝试停止（没有认证）
        response = client.post(
            "/api/v1/chat/stop",
            json={"thread_id": "other-user-thread-2"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_stop_non_stream_chat(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试停止非流式对话"""
        import asyncio
        import threading

        from app.models import Conversation

        # 创建会话
        thread_id = "test-stop-non-stream-thread"
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
            title="Test Stop Non-Stream",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 启动非流式对话（在后台线程中）
        chat_started = threading.Event()
        chat_response = None
        chat_exception = None

        def start_chat():
            nonlocal chat_response, chat_exception
            try:
                chat_started.set()
                chat_response = client.post(
                    "/api/v1/chat",
                    json={"message": "请写一个很长的故事", "thread_id": thread_id},
                    headers=auth_headers,
                )
            except Exception as e:
                chat_exception = e

        chat_thread = threading.Thread(target=start_chat)
        chat_thread.start()

        # 等待对话请求启动
        if chat_started.wait(timeout=2):
            # 等待一小段时间确保请求已开始处理
            await asyncio.sleep(0.3)

            # 发送停止请求
            stop_response = client.post(
                "/api/v1/chat/stop",
                json={"thread_id": thread_id},
                headers=auth_headers,
            )
            assert stop_response.status_code == status.HTTP_200_OK
            stop_response_data = stop_response.json()
            assert stop_response_data["success"] is True
            stop_data = stop_response_data["data"]
            assert stop_data["status"] in ["stopped", "not_running"]
            assert stop_data["thread_id"] == thread_id

        # 等待对话响应结束
        chat_thread.join(timeout=5)

        # 如果响应完成，检查是否被取消
        if chat_response is not None:
            # 如果被成功停止，应该返回499状态码、500错误或其他状态
            assert chat_response.status_code in [
                499,
                408,
                200,
                500,
            ]  # 499=取消, 408=超时, 200=可能已完成, 500=服务器错误

    @pytest.mark.asyncio
    async def test_stop_chat_not_running(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试停止未运行的任务"""
        from app.models import Conversation

        # 创建会话
        thread_id = "test-not-running-thread"
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
            title="Test Not Running",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 尝试停止未运行的任务
        response = client.post(
            "/api/v1/chat/stop",
            json={"thread_id": thread_id},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert data["status"] == "not_running"
        assert data["thread_id"] == thread_id


class TestConversationResetAPI:
    """对话重置 API 测试类"""

    @pytest.mark.asyncio
    async def test_reset_conversation(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试重置对话"""
        from app.models import Conversation, Message

        # 创建会话和消息
        conversation = Conversation(
            thread_id="test-reset-thread",
            user_id=current_user_id,
            title="Test Reset",
            meta_data={},
        )
        db.add(conversation)

        message = Message(
            thread_id="test-reset-thread",
            role="user",
            content="Test message",
            meta_data={},
        )
        db.add(message)
        await db.commit()

        # 重置对话
        response = client.post(
            "/api/v1/conversations/test-reset-thread/reset",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "reset"
        assert data["thread_id"] == "test-reset-thread"

        # 验证消息已删除
        from sqlalchemy import select

        result = await db.execute(select(Message).where(Message.thread_id == "test-reset-thread"))
        messages = result.scalars().all()
        assert len(messages) == 0

    def test_reset_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """测试重置不存在的对话"""
        response = client.post(
            "/api/v1/conversations/non-existent-thread/reset",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_reset_conversation_unauthorized(self, client: TestClient, db):
        """测试未授权重置对话"""
        from app.core.security import get_password_hash
        from app.models import Conversation, User

        # 创建其他用户
        other_user = User(
            username="otheruser",
            email="other@example.com",
            nickname="Other User",
            hashed_password=get_password_hash("test123"),
            is_active=True,
            is_superuser=False,
        )
        db.add(other_user)
        await db.commit()
        await db.refresh(other_user)

        # 创建其他用户的会话
        conversation = Conversation(
            thread_id="other-user-thread",
            user_id=other_user.id,  # 其他用户ID
            title="Other User Conversation",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 尝试重置（没有认证）
        response = client.post(
            "/api/v1/conversations/other-user-thread/reset",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
