"""
测试动态图创建功能

验证用户可以通过修改 user_settings 来动态改变 LLM 模型参数
"""

import pytest
import pytest_asyncio

from app.core.checkpointer import close_checkpointer, init_checkpointer
from app.core.lifespan import clear_graph_cache, get_cached_graph


@pytest_asyncio.fixture(scope="module", autouse=True)
async def setup_checkpointer():
    """初始化测试用的 checkpointer"""
    # 使用临时数据库
    checkpointer = await init_checkpointer(":memory:")
    yield checkpointer
    # 清理
    await close_checkpointer()


def test_graph_cache_with_different_models():
    """测试不同模型配置会创建不同的图实例"""
    # 清除缓存
    clear_graph_cache()

    # 创建第一个图实例
    graph1 = get_cached_graph(
        llm_model="Qwen/Qwen3-8B",
        max_tokens=4096,
    )

    # 使用相同配置应该返回缓存的实例
    graph2 = get_cached_graph(
        llm_model="Qwen/Qwen3-8B",
        max_tokens=4096,
    )

    # 应该是同一个对象
    assert graph1 is graph2

    # 使用不同配置应该创建新实例
    graph3 = get_cached_graph(
        llm_model="Qwen/Qwen3-72B",
        max_tokens=8192,
    )

    # 应该是不同的对象
    assert graph1 is not graph3

    # 检查缓存信息
    cache_info = get_cached_graph.cache_info()
    assert cache_info.hits >= 1  # 至少有一次缓存命中
    assert cache_info.misses >= 2  # 至少有两次缓存未命中（创建了两个不同的图）


def test_graph_cache_clear():
    """测试清除缓存功能"""
    # 创建一个图实例
    graph1 = get_cached_graph(
        llm_model="Qwen/Qwen3-8B",
        max_tokens=4096,
    )

    # 清除缓存
    clear_graph_cache()

    # 使用相同配置应该创建新实例（因为缓存已清除）
    graph2 = get_cached_graph(
        llm_model="Qwen/Qwen3-8B",
        max_tokens=4096,
    )

    # 应该是不同的对象（因为缓存已清除）
    assert graph1 is not graph2


def test_graph_cache_with_none_values():
    """测试 None 值参数的缓存"""
    # 使用 None 值创建图
    graph1 = get_cached_graph(
        llm_model=None,
        api_key=None,
        base_url=None,
        max_tokens=4096,
    )

    # 使用相同的 None 值应该返回缓存的实例
    graph2 = get_cached_graph(
        llm_model=None,
        api_key=None,
        base_url=None,
        max_tokens=4096,
    )

    assert graph1 is graph2


def test_graph_cache_lru_behavior():
    """测试 LRU 缓存行为"""
    clear_graph_cache()

    # 创建多个不同配置的图实例
    graphs = []
    for i in range(5):
        graph = get_cached_graph(
            llm_model=f"model-{i}",
            max_tokens=4096 + i * 1024,
        )
        graphs.append(graph)

    # 检查缓存信息
    cache_info = get_cached_graph.cache_info()
    assert cache_info.currsize == 5  # 当前缓存了 5 个实例
    assert cache_info.misses == 5  # 5 次未命中（都是新创建的）

    # 再次访问第一个配置，应该命中缓存
    graph_reuse = get_cached_graph(
        llm_model="model-0",
        max_tokens=4096,
    )
    assert graph_reuse is graphs[0]

    cache_info = get_cached_graph.cache_info()
    assert cache_info.hits >= 1  # 至少有一次命中


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
