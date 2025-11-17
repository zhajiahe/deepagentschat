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
        response = client.post(
            "/api/v1/conversations",
            json={"title": "Test Conversation", "metadata": {"test": True}},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert "thread_id" in data
        assert data["title"] == "Test Conversation"
        assert data["message_count"] == 0

    @pytest.mark.asyncio
    async def test_list_conversations(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试获取会话列表"""
        from app.models import Conversation

        # 创建几个会话（使用唯一 ID）
        thread_ids = []
        for i in range(3):
            thread_id = str(uuid.uuid4())
            thread_ids.append(thread_id)
            conversation = Conversation(
                thread_id=thread_id,
                user_id=current_user_id,
                title=f"Test Conversation {i}",
                meta_data={},
            )
            db.add(conversation)
        await db.commit()

        # 获取列表
        response = client.get("/api/v1/conversations", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        page_data = data["data"]
        assert "items" in page_data
        assert isinstance(page_data["items"], list)
        assert len(page_data["items"]) >= 3

    @pytest.mark.asyncio
    async def test_get_conversation_detail(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试获取会话详情"""
        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert "conversation" in data
        assert "messages" in data
        assert data["conversation"]["thread_id"] == thread_id
        assert len(data["messages"]) == 1

    @pytest.mark.asyncio
    async def test_update_conversation(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试更新会话"""
        from app.models import Conversation

        # 创建会话（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert data["status"] == "updated"

        # 验证更新
        response = client.get(f"/api/v1/conversations/{thread_id}", headers=auth_headers)
        assert response.json()["data"]["conversation"]["title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_delete_conversation_soft(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试软删除会话"""

        from app.models import Conversation

        # 创建会话（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
        page_data = response.json()["data"]
        conversations = page_data["items"]
        thread_ids_list = [c["thread_id"] for c in conversations]
        assert thread_id not in thread_ids_list

    @pytest.mark.asyncio
    async def test_delete_conversation_hard(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试硬删除会话"""
        from sqlalchemy import select

        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
    async def test_get_messages(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试获取消息列表"""
        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
        response_data = response.json()
        assert response_data["success"] is True
        page_data = response_data["data"]
        assert "items" in page_data
        assert "total" in page_data
        assert page_data["total"] == 5
        assert len(page_data["items"]) == 5

    @pytest.mark.asyncio
    async def test_get_messages_pagination(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试消息分页"""
        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
        response = client.get(
            f"/api/v1/conversations/{thread_id}/messages?page_num=1&page_size=5", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        page_data = response_data["data"]
        assert page_data["page_num"] == 1
        assert page_data["page_size"] == 5
        assert page_data["total"] == 10
        assert len(page_data["items"]) == 5

        # 获取第二页
        response = client.get(
            f"/api/v1/conversations/{thread_id}/messages?page_num=2&page_size=5", headers=auth_headers
        )
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        page_data = response_data["data"]
        assert page_data["page_num"] == 2
        assert page_data["page_size"] == 5
        assert page_data["total"] == 10
        assert len(page_data["items"]) == 5


class TestConversationState:
    """会话状态管理测试类"""

    @pytest.mark.asyncio
    async def test_get_state(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试获取会话状态"""
        from app.models import Conversation

        # 创建会话（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
    async def test_get_checkpoints(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试获取检查点列表"""
        from app.models import Conversation

        # 创建会话（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
            title="Test Checkpoints",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 获取检查点
        response = client.get(f"/api/v1/conversations/{thread_id}/checkpoints", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert "thread_id" in data
        assert "checkpoints" in data
        assert isinstance(data["checkpoints"], list)


class TestConversationExportImport:
    """会话导出导入测试类"""

    @pytest.mark.asyncio
    async def test_export_conversation(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试导出会话"""
        from app.models import Conversation, Message

        # 创建会话和消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert "conversation" in data
        assert "messages" in data
        assert len(data["messages"]) == 3

    @pytest.mark.asyncio
    async def test_import_conversation(self, client: TestClient, auth_headers: dict, db, current_user_id):
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

        # 导入会话（user_id 从认证中获取，不需要在请求中提供）
        response = client.post(
            "/api/v1/conversations/import",
            json={"data": import_data},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert "thread_id" in data
        assert data["status"] == "imported"

        # 验证导入的会话存在
        thread_id = data["thread_id"]
        response = client.get(f"/api/v1/conversations/{thread_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        # 验证响应格式正确
        imported_data = response.json()["data"]
        assert imported_data["conversation"]["thread_id"] == thread_id
        assert imported_data["conversation"]["title"] == "Imported Conversation"
        assert len(imported_data["messages"]) == 2


@pytest.mark.skip(reason="regenerate 接口已移除")
class TestMessageRegenerate:
    """消息重新生成测试类"""

    @pytest.mark.asyncio
    async def test_regenerate_message(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试重新生成消息"""
        from app.models import Conversation, Message

        # 创建会话和消息
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
            title="Test Regenerate",
            meta_data={},
        )
        db.add(conversation)

        # 创建用户消息
        user_message = Message(
            thread_id=thread_id,
            role="user",
            content="What is 2+2?",
            meta_data={},
        )
        db.add(user_message)

        # 创建助手消息（要重新生成的）
        assistant_message = Message(
            thread_id=thread_id,
            role="assistant",
            content="The answer is 4",
            meta_data={},
        )
        db.add(assistant_message)
        await db.commit()
        await db.refresh(assistant_message)

        # 重新生成消息
        response = client.post(
            f"/api/v1/conversations/{thread_id}/messages/{assistant_message.id}/regenerate",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["success"] is True
        data = response_data["data"]
        assert "thread_id" in data
        assert "response" in data
        assert "duration_ms" in data
        assert data["thread_id"] == thread_id

        # 验证消息已重新生成（应该至少有用户消息和新生成的助手消息）
        # 注意：由于重新生成会删除旧消息并创建新消息，消息数量可能相同或不同
        # 但至少应该有一条用户消息和一条助手消息
        from sqlalchemy import func, select

        count_after = await db.execute(select(func.count(Message.id)).where(Message.thread_id == thread_id))
        messages_after = count_after.scalar() or 0
        assert messages_after >= 2  # 至少应该有用户消息和新生成的助手消息

        # 验证至少应该有一条助手消息
        result = await db.execute(select(Message).where(Message.thread_id == thread_id))
        all_messages = result.scalars().all()
        assistant_messages = [msg for msg in all_messages if msg.role == "assistant"]
        assert len(assistant_messages) >= 1

    @pytest.mark.asyncio
    async def test_regenerate_message_not_found(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试重新生成不存在的消息"""
        from app.models import Conversation

        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
            title="Test",
            meta_data={},
        )
        db.add(conversation)
        await db.commit()

        # 尝试重新生成不存在的消息
        response = client.post(
            f"/api/v1/conversations/{thread_id}/messages/99999/regenerate",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_regenerate_user_message_error(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试重新生成用户消息（应该失败）"""
        from app.models import Conversation, Message

        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
            title="Test",
            meta_data={},
        )
        db.add(conversation)

        user_message = Message(
            thread_id=thread_id,
            role="user",
            content="Test message",
            meta_data={},
        )
        db.add(user_message)
        await db.commit()
        await db.refresh(user_message)

        # 尝试重新生成用户消息（应该失败）
        response = client.post(
            f"/api/v1/conversations/{thread_id}/messages/{user_message.id}/regenerate",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "只能重新生成助手消息" in response.json()["msg"]

    @pytest.mark.asyncio
    async def test_regenerate_message_unauthorized(self, client: TestClient, db, current_user_id):
        """测试未授权重新生成消息"""
        from app.core.security import get_password_hash
        from app.models import Conversation, Message, User

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

        # 创建其他用户的会话和消息
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=other_user.id,
            title="Other User Conversation",
            meta_data={},
        )
        db.add(conversation)

        message = Message(
            thread_id=thread_id,
            role="assistant",
            content="Test",
            meta_data={},
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)

        # 尝试重新生成其他用户的消息（应该失败）
        response = client.post(
            f"/api/v1/conversations/{thread_id}/messages/{message.id}/regenerate",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestConversationReset:
    """会话重置测试类（已在 test_chat_route.py 中测试，这里可以添加更多场景）"""

    @pytest.mark.asyncio
    async def test_reset_conversation_with_messages(self, client: TestClient, auth_headers: dict, db, current_user_id):
        """测试重置包含多条消息的会话"""
        from sqlalchemy import select

        from app.models import Conversation, Message

        # 创建会话和多个消息（使用唯一 ID）
        thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=thread_id,
            user_id=current_user_id,
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
