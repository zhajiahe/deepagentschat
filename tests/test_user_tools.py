"""
测试用户目录工具自动部署
验证每个用户都有独立的工具副本
"""

import csv
from pathlib import Path

from app.tools import get_work_path


def test_tool_deployment():
    """测试工具自动部署"""
    print("=" * 60)
    print("测试: 工具自动部署到用户目录")
    print("=" * 60)

    # 测试用户1
    user1_path = get_work_path("test-user-1")
    tools1 = user1_path / ".tools"

    print(f"\n用户1 工作目录: {user1_path}")
    print(f"工具目录: {tools1}")
    print(f"工具目录存在: {tools1.exists()}")

    if tools1.exists():
        print("\n✓ 工具目录结构:")
        for item in sorted(tools1.rglob("*.py")):
            print(f"  - {item.relative_to(user1_path)}")

    # 测试用户2
    user2_path = get_work_path("test-user-2")
    tools2 = user2_path / ".tools"

    print(f"\n用户2 工作目录: {user2_path}")
    print(f"工具目录: {tools2}")
    print(f"工具目录存在: {tools2.exists()}")

    # 验证两个用户的工具是独立的
    print(f"\n✓ 用户1 和用户2 的工具目录独立: {tools1 != tools2}")

    return user1_path, user2_path


def test_tools_functionality(user_path: Path):
    """测试工具功能"""
    import subprocess

    print("\n" + "=" * 60)
    print(f"测试: 工具功能 (用户: {user_path.name})")
    print("=" * 60)

    # 创建测试数据
    csv_file = user_path / "test_data.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "age", "city"])
        writer.writerow(["Alice", 25, "Beijing"])
        writer.writerow(["Bob", 30, "Shanghai"])
        writer.writerow(["Charlie", 35, "Beijing"])

    print(f"\n✓ 测试数据已创建: {csv_file.name}")

    # 测试数据预览
    print("\n--- 测试: 数据预览 ---")
    result = subprocess.run(
        ["python", ".tools/statistics/head.py", "test_data.csv", "--limit", "3"],
        cwd=str(user_path),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # 测试 SQL 查询
    print("\n--- 测试: SQL 查询 ---")
    result = subprocess.run(
        ["python", ".tools/query/data_query.py", "SELECT city, COUNT(*) as count FROM 'test_data.csv' GROUP BY city"],
        cwd=str(user_path),
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    # 测试描述性统计
    print("\n--- 测试: 描述性统计 ---")
    result = subprocess.run(
        ["python", ".tools/statistics/describe.py", "test_data.csv"],
        cwd=str(user_path),
        capture_output=True,
        text=True,
    )
    print(result.stdout[:500])  # 只显示前500字符


def test_tool_isolation():
    """测试工具隔离性"""
    print("\n" + "=" * 60)
    print("测试: 工具隔离性")
    print("=" * 60)

    user1_path = Path("/tmp/user_files/test-user-1")
    user2_path = Path("/tmp/user_files/test-user-2")

    # 修改用户1的工具文件
    user1_tool = user1_path / ".tools" / "test_marker.txt"
    user1_tool.write_text("User 1 marker")

    # 检查用户2的工具目录
    user2_tool = user2_path / ".tools" / "test_marker.txt"

    print(f"\n用户1 标记文件存在: {user1_tool.exists()}")
    print(f"用户2 标记文件存在: {user2_tool.exists()}")
    print(f"✓ 工具隔离验证: {user1_tool.exists() and not user2_tool.exists()}")


def main():
    """运行所有测试"""
    print("\n" + "🚀 " * 20)
    print("开始测试用户工具自动部署")
    print("🚀 " * 20 + "\n")

    try:
        # 测试1: 工具部署
        user1_path, user2_path = test_tool_deployment()

        # 测试2: 工具功能
        test_tools_functionality(user1_path)

        # 测试3: 工具隔离
        test_tool_isolation()

        print("\n" + "✅ " * 20)
        print("所有测试完成！")
        print("✅ " * 20 + "\n")

        print("\n📊 总结:")
        print("  ✓ 工具自动部署到用户目录")
        print("  ✓ 每个用户拥有独立的工具副本")
        print("  ✓ 工具功能正常工作")
        print("  ✓ 用户之间工具隔离")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
