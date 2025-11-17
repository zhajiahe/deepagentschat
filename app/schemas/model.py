"""
模型相关 Schema

用于模型列表相关的数据验证和序列化
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelInfo(BaseModel):
    """模型信息"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "Qwen/Qwen3-8B",
                "object": "model",
                "created": 1234567890,
                "owned_by": "SiliconFlow",
            }
        }
    )

    id: str = Field(..., description="模型唯一标识符")
    object: str = Field(default="model", description="对象类型")
    created: int = Field(..., description="创建时间戳")
    owned_by: str = Field(..., description="模型所有者/提供商")


class ModelListResponse(BaseModel):
    """模型列表响应"""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "models": [
                    {
                        "id": "Qwen/Qwen3-8B",
                        "object": "model",
                        "created": 1234567890,
                        "owned_by": "SiliconFlow",
                    },
                    {
                        "id": "Qwen/Qwen3-72B",
                        "object": "model",
                        "created": 1234567891,
                        "owned_by": "SiliconFlow",
                    },
                ],
                "total": 2,
            }
        }
    )

    models: list[ModelInfo] = Field(..., description="模型列表")
    total: int = Field(..., description="模型总数")
