"""
测试模型管理 API

测试可用模型列表接口
"""

from fastapi.testclient import TestClient


class TestModelsAPI:
    """模型管理 API 测试"""

    def test_list_available_models(self, client: TestClient, auth_headers: dict):
        """测试获取可用模型列表"""
        response = client.get("/api/v1/users/models/available", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["code"] == 200
        assert "data" in data

        # 验证返回的是字符串列表
        models = data["data"]
        assert isinstance(models, list)
        assert len(models) > 0

        # 验证每个元素都是字符串（模型 ID）
        for model_id in models:
            assert isinstance(model_id, str)
            assert len(model_id) > 0

    def test_list_available_models_unauthorized(self, client: TestClient):
        """测试未授权访问模型列表"""
        response = client.get("/api/v1/users/models/available")

        # 未授权访问可能返回 401 或 403
        assert response.status_code in [401, 403]

    def test_model_ids_format(self, client: TestClient, auth_headers: dict):
        """测试模型 ID 格式"""
        response = client.get("/api/v1/users/models/available", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        models = data["data"]

        # 验证模型 ID 格式（通常包含 / 或 -）
        for model_id in models:
            # 模型 ID 应该是有意义的字符串
            assert len(model_id) > 3
            # 大多数模型 ID 包含特定字符
            assert any(char in model_id for char in ["/", "-", "_"])

    def test_common_models_present(self, client: TestClient, auth_headers: dict):
        """测试常见模型是否存在"""
        response = client.get("/api/v1/users/models/available", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        models = data["data"]

        # 验证至少包含一些常见的模型关键词
        model_str = " ".join(models).lower()
        # 至少应该包含 Qwen 或其他常见模型
        assert any(keyword in model_str for keyword in ["qwen", "deepseek", "gpt"])
