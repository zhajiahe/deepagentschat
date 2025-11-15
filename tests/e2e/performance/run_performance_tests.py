#!/usr/bin/env python3
"""
对话接口性能测试运行脚本

运行不同并发用户数量的性能测试场景
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_locust_test(users: int, run_time: str = "1m", base_url: str = "http://localhost:8000"):
    """
    运行 Locust 性能测试

    Args:
        users: 并发用户数
        run_time: 运行时间
        base_url: API 基础URL
    """
    print(f"\n{'='*60}")
    print(f"🚀 开始性能测试: {users} 个并发用户")
    print(f"⏱️  运行时间: {run_time}")
    print(f"🌐 目标URL: {base_url}")
    print(f"{'='*60}")

    # 设置环境变量
    env = os.environ.copy()
    env["PERF_TEST_BASE_URL"] = base_url

    # 构建命令
    cmd = [
        sys.executable,
        "-m",
        "locust",
        "-f",
        "chat_performance_test.py",  # 指定测试文件
        "--config",
        "locust.conf",
        "--users",
        str(users),
        "--spawn-rate",
        str(min(users, 5)),  # 生成速率不超过5 users/s
        "--run-time",
        run_time,
        "--headless",  # 无头模式，不启动Web界面
        "--only-summary",  # 只显示摘要
    ]

    # 运行测试
    try:
        result = subprocess.run(cmd, cwd=Path(__file__).parent, env=env, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ 测试失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️  测试被用户中断")
        return False


def run_scenario_tests(base_url: str = "http://localhost:8000") -> bool:
    """
    运行所有测试场景

    Args:
        base_url: API 基础URL
    """
    scenarios = [
        {"users": 1, "run_time": "30s", "description": "单用户基准测试"},
        {"users": 5, "run_time": "1m", "description": "5用户并发测试"},
        # {"users": 10, "run_time": "2m", "description": "10用户高并发测试"},
    ]

    print("🎯 开始对话接口性能测试套件")
    print(f"目标服务: {base_url}")

    results = []

    for scenario in scenarios:
        users_count = int(scenario["users"])  # type: ignore[arg-type]
        success = run_locust_test(users=users_count, run_time=str(scenario["run_time"]), base_url=base_url)
        results.append({"scenario": scenario, "success": success})

    # 输出总结报告
    print(f"\n{'='*60}")
    print("📊 性能测试总结报告")
    print(f"{'='*60}")

    all_passed = True
    for result in results:
        scenario = result["scenario"]
        status = "✅ 通过" if result["success"] else "❌ 失败"
        print(f"{status} {scenario['users']}用户 - {scenario['description']}")
        if not result["success"]:
            all_passed = False

    print(f"\n{'🎉' if all_passed else '⚠️'} 总体结果: {'所有测试通过' if all_passed else '部分测试失败'}")

    return all_passed


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="对话接口性能测试")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API 基础URL (默认: http://localhost:8000)")
    parser.add_argument(
        "--scenario",
        choices=["1", "5", "10", "all"],
        default="all",
        help="测试场景: 1(单用户), 5(5用户), 10(10用户), all(全部)",
    )
    parser.add_argument("--run-time", default="", help="单场景运行时间 (e.g., 30s, 1m, 2m)")

    args = parser.parse_args()

    # 检查服务是否可访问
    try:
        import requests  # type: ignore[import-untyped]

        response = requests.get(f"{args.base_url}/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ 服务健康检查失败: {response.status_code}")
            return 1
        print(f"✅ 服务健康检查通过: {args.base_url}")
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        print("请确保 FastAPI 服务正在运行")
        return 1

    # 运行测试
    if args.scenario == "all":
        success = run_scenario_tests(args.base_url)
    else:
        users = int(args.scenario)
        run_time = args.run_time or ("30s" if users == 1 else "1m" if users == 5 else "2m")
        success = run_locust_test(users, run_time, args.base_url)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
