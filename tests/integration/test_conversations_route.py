"""
会话管理 API 集成测试

包含会话 CRUD、状态管理、导出导入等功能的真实集成测试
"""

import uuid

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestConversationCRUD:
    """会话 CRUD 测试类"""

    @pytest.mark.asyncio
    async def test_create_conversation(self, client: TestClient, auth_headers: dict, db):
        """测试创建会话"""
        # 注意：API 实际不需要 user_id，从 current_user 获取
        # 但 schema 中定义了 user_id，需要检查实际 API 实现
        response = client.post(
            "/api/v1/conversations",
            json={"user_id": 1, "title": "Test Conversation", "metadata": {"test": True}},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "thread_id" in data
        assert data["title"] == "Test Conversation"
        assert data["message_count"] == 0

    @pytest.mark.asyncio
    async def test_list_conversations(self, client: TestClient, auth_headers: dict, db):
        """测试获取会话列表"""
        from app.models import Conversation

        # 创建几个会话（使用唯一 ID）
        thread_ids = []
        for i in range(3):
            thread_id = str(uuid.uuid4())
            thread_ids.append(thread_id)
            conversation = Conversation(
                thread_id=thread_id,
                user_id=1,
                title=f"Test Conversation {i}",
                meta_data={},
            )
            db.add(conversation)
        await db.commit()

        # 获取列表
        response = client.get("/api/v1/conversations", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        conversations = response.json()
        assert isinstance(conversations, list)
        assert len(conversations) >= 3

    @pytest.mark.asyncio
    async def test_get_conversation_detail(self, client: TestClient, auth_headers: dict, db):
        """测试获取会话详情"""
        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="Test Detail",
            meta_data={},
        )
        db.add(conversation)

        message = Message(
            thread_id=thread_id,
            role="user",
            content="Test message",
            meta_data={},
        )
        db.add(message)
        await db.commit()

        # 获取详情
        response = client.get(f"/api/v1/conversations/{thread_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "conversation" in data
        assert "messages" in data
        assert data["conversation"]["thread_id"] == thread_id
        assert len(data["messages"]) == 1

    @pytest.mark.asyncio
    async def test_update_conversation(self, client: TestClient, auth_headers: dict, db):
        """测试更新会话"""
        from app.models import Conversation

        # 创建会话（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="Original Title",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 更新会话
        response = client.patch(
            f"/api/v1/conversations/{thread_id}",
            json={"title": "Updated Title", "metadata": {"updated": True}},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "updated"

        # 验证更新
        response = client.get(f"/api/v1/conversations/{thread_id}", headers=auth_headers)
        assert response.json()["conversation"]["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_conversation_soft(self, client: TestClient, auth_headers: dict, db):
        """测试软删除会话"""

        from app.models import Conversation

        # 创建会话（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="To Delete",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 软删除
        response = client.delete(f"/api/v1/conversations/{thread_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

        # 验证会话已软删除（不在列表中）
        response = client.get("/api/v1/conversations", headers=auth_headers)
        conversations = response.json()
        thread_ids_list = [c["thread_id"] for c in conversations]
        assert thread_id not in thread_ids_list

    @pytest.mark.asyncio
    async def test_delete_conversation_hard(self, client: TestClient, auth_headers: dict, db):
        """测试硬删除会话"""
        from sqlalchemy import select

        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="To Hard Delete",
            meta_data={},
        )
        db.add(conversation)

        message = Message(
            thread_id=thread_id,
            role="user",
            content="Test",
            meta_data={},
        )
        db.add(message)
        await db.commit()

        # 硬删除
        response = client.delete(f"/api/v1/conversations/{thread_id}?hard_delete=true", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK

        # 验证会话和消息都已删除
        result = await db.execute(select(Conversation).where(Conversation.thread_id == thread_id))
        assert result.scalar_one_or_none() is None

        result = await db.execute(select(Message).where(Message.thread_id == thread_id))
        assert len(result.scalars().all()) == 0

    def test_get_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的会话"""
        response = client.get("/api/v1/conversations/non-existent-thread", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """测试更新不存在的会话"""
        response = client.patch(
            "/api/v1/conversations/non-existent-thread",
            json={"title": "New Title"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_conversation_not_found(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的会话"""
        response = client.delete("/api/v1/conversations/non-existent-thread", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_conversation_unauthorized(self, client: TestClient, db):
        """测试未授权访问会话"""
        response = client.get("/api/v1/conversations")
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestConversationMessages:
    """会话消息管理测试类"""

    @pytest.mark.asyncio
    async def test_get_messages(self, client: TestClient, auth_headers: dict, db):
        """测试获取消息列表"""
        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="Test Messages",
            meta_data={},
        )
        db.add(conversation)

        for i in range(5):
            message = Message(
                thread_id=thread_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                meta_data={},
            )
            db.add(message)
        await db.commit()

        # 获取消息
        response = client.get(f"/api/v1/conversations/{thread_id}/messages", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()
        assert len(messages) == 5

    @pytest.mark.asyncio
    async def test_get_messages_pagination(self, client: TestClient, auth_headers: dict, db):
        """测试消息分页"""
        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="Test Pagination",
            meta_data={},
        )
        db.add(conversation)

        for i in range(10):
            message = Message(
                thread_id=thread_id,
                role="user",
                content=f"Message {i}",
                meta_data={},
            )
            db.add(message)
        await db.commit()

        # 获取第一页
        response = client.get(f"/api/v1/conversations/{thread_id}/messages?skip=0&limit=5", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()
        assert len(messages) == 5

        # 获取第二页
        response = client.get(f"/api/v1/conversations/{thread_id}/messages?skip=5&limit=5", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        messages = response.json()
        assert len(messages) == 5


class TestConversationState:
    """会话状态管理测试类"""

    @pytest.mark.asyncio
    async def test_get_state(self, client: TestClient, auth_headers: dict, db):
        """测试获取会话状态"""
        from app.models import Conversation

        # 创建会话（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="Test State",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 获取状态（可能为空，因为还没有执行过图）
        response = client.get(f"/api/v1/conversations/{thread_id}/state", headers=auth_headers)
        # 状态可能不存在，所以可能是 404 或 200
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

    @pytest.mark.asyncio
    async def test_get_checkpoints(self, client: TestClient, auth_headers: dict, db):
        """测试获取检查点列表"""
        from app.models import Conversation

        # 创建会话（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="Test Checkpoints",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 获取检查点
        response = client.get(f"/api/v1/conversations/{thread_id}/checkpoints", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "thread_id" in data
        assert "checkpoints" in data
        assert isinstance(data["checkpoints"], list)


class TestConversationExportImport:
    """会话导出导入测试类"""

    @pytest.mark.asyncio
    async def test_export_conversation(self, client: TestClient, auth_headers: dict, db):
        """测试导出会话"""
        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="Test Export",
            meta_data={"key": "value"},
        )
        db.add(conversation)

        for i in range(3):
            message = Message(
                thread_id=thread_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                meta_data={},
            )
            db.add(message)
        await db.commit()

        # 导出会话
        response = client.get(f"/api/v1/conversations/{thread_id}/export", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "conversation" in data
        assert "messages" in data
        assert len(data["messages"]) == 3

    @pytest.mark.asyncio
    async def test_import_conversation(self, client: TestClient, auth_headers: dict, db):
        """测试导入会话"""
        # 准备导入数据
        import_data = {
            "conversation": {
                "title": "Imported Conversation",
                "metadata": {"imported": True},
            },
            "messages": [
                {"role": "user", "content": "Hello", "metadata": {}},
                {"role": "assistant", "content": "Hi there", "metadata": {}},
            ],
        }

        # 导入会话
        response = client.post(
            "/api/v1/conversations/import",
            json={"user_id": 1, "data": import_data},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "thread_id" in data
        assert data["status"] == "imported"

        # 验证导入的会话存在
        thread_id = data["thread_id"]
        response = client.get(f"/api/v1/conversations/{thread_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        conv_data = response.json()
        assert conv_data["conversation"]["title"] == "Imported Conversation"
        assert len(conv_data["messages"]) == 2


class TestConversationReset:
    """会话重置测试类（已在 test_chat_route.py 中测试，这里可以添加更多场景）"""

    @pytest.mark.asyncio
    async def test_reset_conversation_with_messages(self, client: TestClient, auth_headers: dict, db):
        """测试重置包含多条消息的会话"""
        from sqlalchemy import select

        from app.models import Conversation, Message

        # 创建会话和多个消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=1,
            title="Test Reset Multi",
            meta_data={},
        )
        db.add(conversation)

        for i in range(10):
            message = Message(
                thread_id=thread_id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
                meta_data={},
            )
            db.add(message)
        await db.commit()

        # 重置会话
        response = client.post(f"/api/v1/conversations/{thread_id}/reset", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "reset"
        assert "10" in data["message"]  # 应该显示删除了10条消息

        # 验证消息已删除
        result = await db.execute(select(Message).where(Message.thread_id == thread_id))
        messages = result.scalars().all()
        assert len(messages) == 0
