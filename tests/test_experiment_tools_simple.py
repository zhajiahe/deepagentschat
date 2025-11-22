"""
简化的 experiment_tools 集成测试
直接调用命令行工具，不通过 LangChain
"""

import csv
import json
import subprocess
from pathlib import Path


def run_command(cmd: str, cwd: str) -> str:
    """运行命令并返回输出"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"错误: {e}"


def test_file_operations():
    """测试文件读写工具"""
    print("=" * 60)
    print("测试 1: 文件读写工具")
    print("=" * 60)

    work_path = Path("/tmp/user_files/test-user")
    work_path.mkdir(parents=True, exist_ok=True)

    # 创建测试文件
    test_file = work_path / "test.txt"
    test_file.write_text("Hello, World!\n这是测试文件。\n支持中文。")

    # 测试读取文件
    result = run_command(
        "python /tmp/user_files/.tools/files/read_file.py test.txt",
        str(work_path),
    )
    print("\n✓ 文件读取结果:")
    print(result)


def test_url_reading():
    """测试 URL 读取工具"""
    print("\n" + "=" * 60)
    print("测试 2: URL 读取工具")
    print("=" * 60)

    work_path = Path("/tmp/user_files/test-user")

    # 测试读取 JSON API
    result = run_command(
        "python /tmp/user_files/.tools/files/read_url.py https://httpbin.org/json --timeout 10",
        str(work_path),
    )
    print("\n✓ URL 读取结果 (JSON API):")
    print(result[:500] + "..." if len(result) > 500 else result)


def test_data_analysis():
    """测试数据分析工具"""
    print("\n" + "=" * 60)
    print("测试 3: 数据分析工具")
    print("=" * 60)

    work_path = Path("/tmp/user_files/test-user")

    # 创建测试 CSV 文件
    csv_file = work_path / "sales.csv"
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["product", "category", "amount", "date"])
        writer.writerow(["iPhone 14", "Electronics", 999, "2024-01-15"])
        writer.writerow(["MacBook Pro", "Electronics", 2499, "2024-01-16"])
        writer.writerow(["iPad Air", "Electronics", 599, "2024-01-17"])
        writer.writerow(["AirPods Pro", "Electronics", 249, "2024-01-18"])
        writer.writerow(["Apple Watch", "Electronics", 399, "2024-01-19"])
        writer.writerow(["iPhone 14", "Electronics", 999, "2024-01-20"])
        writer.writerow(["MacBook Pro", "Electronics", 2499, "2024-01-21"])

    print("\n✓ 测试数据已创建: sales.csv")

    # 测试数据预览
    print("\n--- 数据预览 (head) ---")
    result = run_command(
        "python /tmp/user_files/.tools/statistics/head.py sales.csv --limit 5",
        str(work_path),
    )
    print(result)

    # 测试描述性统计
    print("\n--- 描述性统计 (describe) ---")
    result = run_command(
        "python /tmp/user_files/.tools/statistics/describe.py sales.csv",
        str(work_path),
    )
    print(result)

    # 测试唯一值分析
    print("\n--- 唯一值分析 (unique) ---")
    result = run_command(
        "python /tmp/user_files/.tools/statistics/unique.py sales.csv --topk 5",
        str(work_path),
    )
    print(result)


def test_sql_query():
    """测试 SQL 查询工具"""
    print("\n" + "=" * 60)
    print("测试 4: SQL 查询工具")
    print("=" * 60)

    work_path = Path("/tmp/user_files/test-user")

    # 基本查询
    print("\n--- SQL 查询: 基本查询 ---")
    result = run_command(
        "python /tmp/user_files/.tools/query/data_query.py \"SELECT * FROM 'sales.csv' LIMIT 3\"",
        str(work_path),
    )
    print(result)

    # 聚合查询
    print("\n--- SQL 查询: 聚合分析 ---")
    result = run_command(
        "python /tmp/user_files/.tools/query/data_query.py \"SELECT product, COUNT(*) as count, SUM(amount) as total FROM 'sales.csv' GROUP BY product ORDER BY total DESC\"",
        str(work_path),
    )
    print(result)

    # 条件查询
    print("\n--- SQL 查询: 条件过滤 ---")
    result = run_command(
        "python /tmp/user_files/.tools/query/data_query.py \"SELECT * FROM 'sales.csv' WHERE amount > 500\"",
        str(work_path),
    )
    print(result)


def test_json_data():
    """测试 JSON 数据处理"""
    print("\n" + "=" * 60)
    print("测试 5: JSON 数据处理")
    print("=" * 60)

    work_path = Path("/tmp/user_files/test-user")

    # 创建测试 JSON 文件
    json_file = work_path / "users.json"
    users = [
        {"id": 1, "name": "Alice", "age": 25, "city": "Beijing"},
        {"id": 2, "name": "Bob", "age": 30, "city": "Shanghai"},
        {"id": 3, "name": "Charlie", "age": 35, "city": "Beijing"},
        {"id": 4, "name": "David", "age": 28, "city": "Shenzhen"},
        {"id": 5, "name": "Eve", "age": 32, "city": "Beijing"},
    ]
    with open(json_file, "w", encoding="utf-8") as f:
        for user in users:
            f.write(json.dumps(user, ensure_ascii=False) + "\n")

    print("\n✓ 测试数据已创建: users.json")

    # 测试 JSON 查询
    print("\n--- JSON 查询: 按城市统计 ---")
    result = run_command(
        "python /tmp/user_files/.tools/query/data_query.py \"SELECT city, COUNT(*) as count, AVG(age) as avg_age FROM 'users.json' GROUP BY city ORDER BY count DESC\"",
        str(work_path),
    )
    print(result)


def test_complex_workflow():
    """测试复杂工作流"""
    print("\n" + "=" * 60)
    print("测试 6: 复杂数据分析工作流")
    print("=" * 60)

    work_path = Path("/tmp/user_files/test-user")

    # 1. 数据探索
    print("\n--- 步骤 1: 数据探索 ---")
    result = run_command(
        "python /tmp/user_files/.tools/statistics/head.py sales.csv --limit 3",
        str(work_path),
    )
    print("数据预览:", result[:300])

    # 2. 数据分析
    print("\n--- 步骤 2: 数据分析 ---")
    result = run_command(
        "python /tmp/user_files/.tools/query/data_query.py \"SELECT category, COUNT(*) as products, SUM(amount) as revenue FROM 'sales.csv' GROUP BY category\"",
        str(work_path),
    )
    print("分析结果:", result)

    # 3. 数据导出
    print("\n--- 步骤 3: 数据导出 ---")
    result = run_command(
        "python /tmp/user_files/.tools/query/data_query.py \"COPY (SELECT * FROM 'sales.csv' WHERE amount > 500) TO 'high_value_sales.csv'\"",
        str(work_path),
    )
    print("导出结果:", result)

    # 验证导出
    result = run_command(
        "ls -lh high_value_sales.csv && wc -l high_value_sales.csv",
        str(work_path),
    )
    print("文件验证:", result)


def main():
    """运行所有测试"""
    print("\n" + "🚀 " * 20)
    print("开始测试 experiment_tools 集成")
    print("🚀 " * 20 + "\n")

    try:
        test_file_operations()
        test_url_reading()
        test_data_analysis()
        test_sql_query()
        test_json_data()
        test_complex_workflow()

        print("\n" + "✅ " * 20)
        print("所有测试完成！")
        print("✅ " * 20 + "\n")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
