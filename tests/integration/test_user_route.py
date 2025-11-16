"""
用户 API 集成测试

包含用户管理和认证相关的测试
"""

from fastapi import status
from fastapi.testclient import TestClient


class TestAuthAPI:
    """认证 API 测试类"""

    def test_register(self, client: TestClient):
        """测试用户注册"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "nickname": "New User",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "newuser"
        assert data["data"]["is_active"] is True
        assert data["data"]["is_superuser"] is False

    def test_register_duplicate_username(self, client: TestClient):
        """测试注册重复用户名"""
        # 第一次注册
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test1@example.com",
                "nickname": "Test",
                "password": "password123",
            },
        )
        # 第二次注册相同用户名
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test2@example.com",
                "nickname": "Test",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "用户名已存在" in response.json()["msg"]

    def test_login_success(self, client: TestClient):
        """测试登录成功"""
        # 先注册用户
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "nickname": "Login User",
                "password": "password123",
            },
        )
        # 登录
        response = client.post("/api/v1/auth/login?username=loginuser&password=password123")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient):
        """测试登录密码错误"""
        # 先注册用户
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "wrongpwduser",
                "email": "wrongpwd@example.com",
                "nickname": "Wrong Password User",
                "password": "correct_password",
            },
        )
        # 使用错误密码登录
        response = client.post("/api/v1/auth/login?username=wrongpwduser&password=wrong_password")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "用户名或密码错误" in response.json()["msg"]

    def test_login_user_not_exist(self, client: TestClient):
        """测试登录用户不存在"""
        response = client.post("/api/v1/auth/login?username=nonexistent&password=password123")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self, client: TestClient):
        """测试获取当前用户信息"""
        # 注册并登录
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "currentuser",
                "email": "current@example.com",
                "nickname": "Current User",
                "password": "password123",
            },
        )
        login_response = client.post("/api/v1/auth/login?username=currentuser&password=password123")
        token = login_response.json()["data"]["access_token"]

        # 获取当前用户信息
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "currentuser"

    def test_get_current_user_without_token(self, client: TestClient):
        """测试未登录获取当前用户信息"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_current_user(self, client: TestClient):
        """测试更新当前用户信息"""
        # 注册并登录
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "updateme",
                "email": "updateme@example.com",
                "nickname": "Update Me",
                "password": "password123",
            },
        )
        login_response = client.post("/api/v1/auth/login?username=updateme&password=password123")
        token = login_response.json()["data"]["access_token"]

        # 更新用户信息
        response = client.put(
            "/api/v1/auth/me",
            json={"nickname": "Updated Name", "email": "updated@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["nickname"] == "Updated Name"
        assert data["data"]["email"] == "updated@example.com"

    def test_change_password(self, client: TestClient):
        """测试修改密码"""
        # 注册并登录
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "changepwd",
                "email": "changepwd@example.com",
                "nickname": "Change Password",
                "password": "old_password",
            },
        )
        login_response = client.post("/api/v1/auth/login?username=changepwd&password=old_password")
        token = login_response.json()["data"]["access_token"]

        # 修改密码
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"old_password": "old_password", "new_password": "new_password"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

        # 用新密码登录
        new_login_response = client.post("/api/v1/auth/login?username=changepwd&password=new_password")
        assert new_login_response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old_password(self, client: TestClient):
        """测试修改密码时旧密码错误"""
        # 注册并登录
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "wrongoldpwd",
                "email": "wrongoldpwd@example.com",
                "nickname": "Wrong Old Password",
                "password": "correct_password",
            },
        )
        login_response = client.post("/api/v1/auth/login?username=wrongoldpwd&password=correct_password")
        token = login_response.json()["data"]["access_token"]

        # 使用错误的旧密码修改
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"old_password": "wrong_password", "new_password": "new_password"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "旧密码错误" in response.json()["msg"]


class TestUserAPI:
    """用户管理 API 测试类（需要超级管理员权限）"""

    def test_create_user(self, client: TestClient, auth_headers: dict):
        """测试创建用户"""
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        response = client.post(
            "/api/v1/users",
            json={
                "username": f"testuser_{unique_id}",
                "email": f"test_{unique_id}@example.com",
                "nickname": "Test User",
                "password": "test123456",
                "is_active": True,
                "is_superuser": False,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["code"] == 201
        assert data["data"]["username"] == f"testuser_{unique_id}"
        assert data["data"]["email"] == f"test_{unique_id}@example.com"
        assert "id" in data["data"]

    def test_create_user_duplicate_username(self, client: TestClient, auth_headers: dict):
        """测试创建重复用户名的用户"""
        # 第一次创建
        client.post(
            "/api/v1/users",
            json={
                "username": "duplicate",
                "email": "user1@example.com",
                "nickname": "User 1",
                "password": "test123456",
            },
            headers=auth_headers,
        )
        # 第二次创建相同用户名
        response = client.post(
            "/api/v1/users",
            json={
                "username": "duplicate",
                "email": "user2@example.com",
                "nickname": "User 2",
                "password": "test123456",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "用户名已存在" in response.json()["msg"]

    def test_create_user_invalid_email(self, client: TestClient, auth_headers: dict):
        """测试创建用户时邮箱格式错误"""
        response = client.post(
            "/api/v1/users",
            json={
                "username": "testuser",
                "email": "not-an-email-at-all",
                "nickname": "Test User",
                "password": "test123456",
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    def test_get_users(self, client: TestClient, auth_headers: dict):
        """测试获取用户列表"""
        # 创建几个测试用户
        for i in range(3):
            client.post(
                "/api/v1/users",
                json={
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                    "nickname": f"User {i}",
                    "password": "test123456",
                },
                headers=auth_headers,
            )

        # 获取用户列表
        response = client.get("/api/v1/users", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 3
        assert len(data["data"]["items"]) >= 3

    def test_get_users_with_pagination(self, client: TestClient, auth_headers: dict):
        """测试分页获取用户列表"""
        # 创建10个用户
        for i in range(10):
            client.post(
                "/api/v1/users",
                json={
                    "username": f"pageuser{i}",
                    "email": f"pageuser{i}@example.com",
                    "nickname": f"Page User {i}",
                    "password": "test123456",
                },
                headers=auth_headers,
            )

        # 测试分页
        response = client.get("/api/v1/users?page_num=1&page_size=5", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["page_num"] == 1
        assert data["data"]["page_size"] == 5
        assert len(data["data"]["items"]) == 5

    def test_get_users_with_keyword_search(self, client: TestClient, auth_headers: dict):
        """测试关键词搜索"""
        # 创建测试用户
        client.post(
            "/api/v1/users",
            json={
                "username": "searchuser",
                "email": "search@example.com",
                "nickname": "Search User",
                "password": "test123456",
            },
            headers=auth_headers,
        )

        # 搜索用户
        response = client.get("/api/v1/users?keyword=search", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1
        assert any("search" in item["username"].lower() for item in data["data"]["items"])

    def test_get_user_by_id(self, client: TestClient, auth_headers: dict):
        """测试根据ID获取用户"""
        # 创建用户
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": "getuser",
                "email": "getuser@example.com",
                "nickname": "Get User",
                "password": "test123456",
            },
            headers=auth_headers,
        )
        user_id = create_response.json()["data"]["id"]

        # 获取用户
        response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == user_id
        assert data["data"]["username"] == "getuser"

    def test_get_user_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的用户"""
        import uuid

        non_existent_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/users/{non_existent_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "用户不存在" in response.json()["msg"]

    def test_update_user(self, client: TestClient, auth_headers: dict):
        """测试更新用户"""
        import uuid

        unique_id = str(uuid.uuid4())[:8]
        # 创建用户
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": f"updateuser_{unique_id}",
                "email": f"update_{unique_id}@example.com",
                "nickname": "Update User",
                "password": "test123456",
            },
            headers=auth_headers,
        )
        user_id = create_response.json()["data"]["id"]

        # 更新用户
        updated_email = f"updated_{unique_id}@example.com"
        response = client.put(
            f"/api/v1/users/{user_id}",
            json={"nickname": "Updated User", "email": updated_email},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["nickname"] == "Updated User"
        assert data["data"]["email"] == updated_email

    def test_update_user_not_found(self, client: TestClient, auth_headers: dict):
        """测试更新不存在的用户"""
        import uuid

        non_existent_id = str(uuid.uuid4())
        response = client.put(f"/api/v1/users/{non_existent_id}", json={"nickname": "Test"}, headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_user(self, client: TestClient, auth_headers: dict):
        """测试删除用户"""
        # 创建用户
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": "deleteuser",
                "email": "delete@example.com",
                "nickname": "Delete User",
                "password": "test123456",
            },
            headers=auth_headers,
        )
        user_id = create_response.json()["data"]["id"]

        # 删除用户
        response = client.delete(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

        # 验证用户已删除
        get_response = client.get(f"/api/v1/users/{user_id}", headers=auth_headers)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_user_not_found(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的用户"""
        import uuid

        non_existent_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/users/{non_existent_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestUserSettingsAPI:
    """用户设置 API 测试类"""

    def test_get_user_settings(self, client: TestClient, auth_headers: dict):
        """测试获取用户设置"""
        response = client.get("/api/v1/users/settings", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        settings = data["data"]
        assert "user_id" in settings
        assert "llm_model" in settings
        assert "max_tokens" in settings
        assert "settings" in settings
        assert "config" in settings
        assert "context" in settings

    def test_get_user_settings_creates_default(self, client: TestClient, auth_headers: dict):
        """测试获取用户设置时自动创建默认设置"""
        # 第一次获取应该创建默认设置
        response = client.get("/api/v1/users/settings", headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        settings = data["data"]
        assert "llm_model" in settings
        assert "max_tokens" in settings

    def test_update_user_settings(self, client: TestClient, auth_headers: dict):
        """测试更新用户设置"""
        # 更新设置
        response = client.put(
            "/api/v1/users/settings",
            json={
                "llm_model": "gpt-4",
                "max_tokens": 1000,
                "settings": {"key": "value"},
                "config": {"temperature": 0.7},
                "context": {"user_context": "test"},
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        settings = data["data"]
        assert settings["llm_model"] == "gpt-4"
        assert settings["max_tokens"] == 1000
        assert settings["settings"] == {"key": "value"}
        assert settings["config"] == {"temperature": 0.7}
        assert settings["context"] == {"user_context": "test"}

    def test_update_user_settings_partial(self, client: TestClient, auth_headers: dict):
        """测试部分更新用户设置"""
        # 只更新模型
        response = client.put(
            "/api/v1/users/settings",
            json={"llm_model": "gpt-3.5-turbo"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        settings = data["data"]
        assert settings["llm_model"] == "gpt-3.5-turbo"
        # 其他设置应该保持不变或使用默认值
        assert "max_tokens" in settings

    def test_update_user_settings_invalid_max_tokens(self, client: TestClient, auth_headers: dict):
        """测试更新用户设置时 max_tokens 值无效"""
        # max_tokens 应该大于 0
        response = client.put(
            "/api/v1/users/settings",
            json={"max_tokens": -1},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_user_settings_unauthorized(self, client: TestClient):
        """测试未授权获取用户设置"""
        response = client.get("/api/v1/users/settings")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_settings_unauthorized(self, client: TestClient):
        """测试未授权更新用户设置"""
        response = client.put("/api/v1/users/settings", json={"llm_model": "gpt-4"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
