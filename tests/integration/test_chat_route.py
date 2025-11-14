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
        data = response.json()
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
        data = response.json()
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
