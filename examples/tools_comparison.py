"""
工具系统对比示例

演示 tools.py (进程隔离) 和 tools_docker.py (容器隔离) 的区别
"""

import asyncio
import time

from app.tools import ToolRuntime as ToolRuntimeProcess
from app.tools import UserContext as UserContextProcess
from app.tools import shell_exec as shell_exec_process

try:
    from app.tools_docker import DOCKER_AVAILABLE
    from app.tools_docker import ToolRuntime as ToolRuntimeDocker
    from app.tools_docker import UserContext as UserContextDocker
    from app.tools_docker import shell_exec as shell_exec_docker

    DOCKER_ENABLED = DOCKER_AVAILABLE
except ImportError:
    DOCKER_ENABLED = False
    print("⚠️  Docker 版本未安装，只测试进程版本")


async def test_process_version():
    """测试进程隔离版本"""
    print("\n" + "=" * 50)
    print("测试进程隔离版本 (tools.py)")
    print("=" * 50)

    runtime = ToolRuntimeProcess(context=UserContextProcess(user_id="test-user"))

    # 测试 1: 简单命令
    print("\n1. 简单命令 (echo)")
    start = time.time()
    result = await shell_exec_process("echo 'Hello from Process!'", runtime)
    elapsed = time.time() - start
    print(f"   结果: {result.strip()}")
    print(f"   耗时: {elapsed:.3f}s")

    # 测试 2: Python 脚本
    print("\n2. Python 脚本")
    start = time.time()
    result = await shell_exec_process("python -c 'print(2 + 2)'", runtime)
    elapsed = time.time() - start
    print(f"   结果: {result.strip()}")
    print(f"   耗时: {elapsed:.3f}s")

    # 测试 3: 数据分析
    print("\n3. 数据分析 (pandas)")
    start = time.time()
    result = await shell_exec_process("python -c 'import pandas; print(pandas.__version__)'", runtime)
    elapsed = time.time() - start
    print(f"   结果: {result.strip()}")
    print(f"   耗时: {elapsed:.3f}s")

    # 测试 4: 文件操作
    print("\n4. 文件操作")
    start = time.time()
    result = await shell_exec_process("echo 'test data' > test.txt && cat test.txt", runtime)
    elapsed = time.time() - start
    print(f"   结果: {result.strip()}")
    print(f"   耗时: {elapsed:.3f}s")


async def test_docker_version():
    """测试 Docker 容器版本"""
    if not DOCKER_ENABLED:
        print("\n⚠️  跳过 Docker 版本测试（未安装）")
        return

    print("\n" + "=" * 50)
    print("测试 Docker 容器版本 (tools_docker.py)")
    print("=" * 50)

    runtime = ToolRuntimeDocker(context=UserContextDocker(user_id="test-user"))

    # 测试 1: 简单命令
    print("\n1. 简单命令 (echo)")
    start = time.time()
    try:
        result = await shell_exec_docker("echo 'Hello from Docker!'", runtime)
        elapsed = time.time() - start
        print(f"   结果: {result.strip()}")
        print(f"   耗时: {elapsed:.3f}s")
    except Exception as e:
        print(f"   错误: {e}")

    # 测试 2: Python 脚本
    print("\n2. Python 脚本")
    start = time.time()
    try:
        result = await shell_exec_docker("python -c 'print(2 + 2)'", runtime)
        elapsed = time.time() - start
        print(f"   结果: {result.strip()}")
        print(f"   耗时: {elapsed:.3f}s")
    except Exception as e:
        print(f"   错误: {e}")

    # 测试 3: 数据分析
    print("\n3. 数据分析 (pandas)")
    start = time.time()
    try:
        result = await shell_exec_docker("python -c 'import pandas; print(pandas.__version__)'", runtime)
        elapsed = time.time() - start
        print(f"   结果: {result.strip()}")
        print(f"   耗时: {elapsed:.3f}s")
    except Exception as e:
        print(f"   错误: {e}")

    # 测试 4: 文件操作
    print("\n4. 文件操作")
    start = time.time()
    try:
        result = await shell_exec_docker("echo 'test data' > test.txt && cat test.txt", runtime)
        elapsed = time.time() - start
        print(f"   结果: {result.strip()}")
        print(f"   耗时: {elapsed:.3f}s")
    except Exception as e:
        print(f"   错误: {e}")


async def test_security():
    """测试安全性"""
    print("\n" + "=" * 50)
    print("安全性测试")
    print("=" * 50)

    runtime_process = ToolRuntimeProcess(context=UserContextProcess(user_id="test-user"))

    # 测试路径遍历
    print("\n1. 路径遍历攻击测试")
    print("   尝试访问父目录...")
    result = await shell_exec_process("ls ../../", runtime_process)
    print(f"   进程版本: {result[:100]}...")

    if DOCKER_ENABLED:
        runtime_docker = ToolRuntimeDocker(context=UserContextDocker(user_id="test-user"))
        try:
            result = await shell_exec_docker("ls ../../", runtime_docker)
            print(f"   Docker版本: {result[:100]}...")
        except Exception as e:
            print(f"   Docker版本: {e}")

    # 测试网络访问
    print("\n2. 网络访问测试")
    print("   尝试访问外部网络...")
    result = await shell_exec_process(
        "curl -s https://www.google.com --max-time 2 || echo 'Network access'", runtime_process
    )
    print(f"   进程版本: {result[:100]}...")

    if DOCKER_ENABLED:
        try:
            result = await shell_exec_docker(
                "curl -s https://www.google.com --max-time 2 || echo 'Network blocked'", runtime_docker
            )
            print(f"   Docker版本: {result[:100]}...")
        except Exception as e:
            print(f"   Docker版本: {e}")


async def main():
    """主函数"""
    print("=" * 50)
    print("工具系统对比测试")
    print("=" * 50)

    # 测试进程版本
    await test_process_version()

    # 测试 Docker 版本
    if DOCKER_ENABLED:
        await test_docker_version()

    # 安全性测试
    await test_security()

    # 总结
    print("\n" + "=" * 50)
    print("总结")
    print("=" * 50)
    print("\n进程版本 (tools.py):")
    print("  ✅ 启动快 (~10-100ms)")
    print("  ✅ 资源占用少")
    print("  ⚠️  隔离性较弱")
    print("  ⚠️  安全风险较高")

    if DOCKER_ENABLED:
        print("\nDocker版本 (tools_docker.py):")
        print("  ✅ 强隔离")
        print("  ✅ 高安全性")
        print("  ✅ 资源可控")
        print("  ⚠️  启动慢 (~1-2s)")
        print("  ⚠️  需要 Docker 环境")

    print("\n推荐使用场景:")
    print("  - 开发环境/可信用户: tools.py")
    print("  - 生产环境/不可信用户: tools_docker.py")


if __name__ == "__main__":
    asyncio.run(main())
