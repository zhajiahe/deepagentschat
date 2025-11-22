"""
DuckDB 数据查询工具
用法: python data_query.py "SELECT * FROM 'data.csv'"
"""

import re
import sys
from pathlib import Path

import duckdb


def main():
    # 检查参数
    if len(sys.argv) < 2:
        print("用法: python data_query.py \"SELECT * FROM 'data.csv'\"")
        print("\n常用示例:")
        print("  python data_query.py \"SELECT * FROM 'data.csv' LIMIT 10\"")
        print("  python data_query.py \"SELECT COUNT(*) FROM 'data.csv'\"")
        print("  python data_query.py \"COPY (SELECT * FROM 'data.xlsx') TO 'output.csv'\"")
        sys.exit(1)

    query = sys.argv[1]

    # 检查引用的文件是否存在
    check_files_exist(query)

    try:
        con = duckdb.connect()

        # 设置合理的默认配置
        con.execute("SET memory_limit='2GB'")
        con.execute("SET threads=4")

        result = con.execute(query)

        # 尝试获取结果
        try:
            df = result.df()

            # 空结果
            if df.empty:
                print("⚠️  查询返回 0 行")
                return

            # 输出结果
            print_result(df)
        except Exception:
            # DDL/DML 语句，无返回结果
            print("✅ 执行成功")
            return

        con.close()

    except duckdb.CatalogException as e:
        print(f"❌ 表或列不存在: {e}", file=sys.stderr)
        sys.exit(1)

    except duckdb.ParserException as e:
        print(f"❌ SQL 语法错误: {e}", file=sys.stderr)
        sys.exit(1)

    except duckdb.IOException as e:
        print(f"❌ 文件读取错误: {e}", file=sys.stderr)
        sys.exit(1)

    except MemoryError:
        print("❌ 内存不足，建议:", file=sys.stderr)
        print("  1. 在查询末尾添加 LIMIT", file=sys.stderr)
        print("  2. 使用 COPY TO 导出: COPY (...) TO 'output.csv'", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"❌ 执行错误: {e}", file=sys.stderr)
        sys.exit(1)


def check_files_exist(query: str):
    """检查 SQL 中引用的文件是否存在"""
    # Skip file check for COPY TO statements (output files don't need to exist)
    if re.search(r"\bCOPY\s*\(.*\)\s*TO\s+", query, re.IGNORECASE):
        return

    # 匹配 'file.ext' 或 "file.ext"
    pattern = r"['\"]([^'\"]+\.(csv|json|parquet|xlsx|xls|jsonl))['\"]"
    files = re.findall(pattern, query, re.IGNORECASE)

    missing = []
    for file_path, _ in files:
        # 跳过通配符
        if "*" in file_path or "?" in file_path:
            continue
        if not Path(file_path).exists():
            missing.append(file_path)

    if missing:
        print("❌ 文件不存在:", file=sys.stderr)
        for f in missing:
            print(f"   {f}", file=sys.stderr)
        sys.exit(1)


def print_result(df):
    """智能输出结果"""
    rows, cols = len(df), len(df.columns)

    # Convert pandas NA to string 'NULL' for better display compatibility with tabulate
    df = df.astype(str).replace("<NA>", "NULL")

    # 小结果：直接输出 markdown 表格
    if rows <= 1000:
        try:
            from tabulate import tabulate  # type: ignore[import-untyped]

            print(tabulate(df, headers="keys", tablefmt="github", showindex=False))
        except ImportError:
            print(df.to_markdown(index=False))

        # 显示统计
        if rows > 50:
            print(f"\n📊 {rows:,} 行 × {cols} 列")

    # 大结果：只显示前 100 行 + 统计
    else:
        print(f"⚠️  结果较大 ({rows:,} 行)，仅显示前 100 行\n")

        try:
            from tabulate import tabulate

            print(tabulate(df.head(100), headers="keys", tablefmt="github", showindex=False))
        except ImportError:
            print(df.head(100).to_markdown(index=False))

        print(f"\n📊 总计: {rows:,} 行 × {cols} 列")
        print("💡 提示: 在查询末尾添加 LIMIT，或使用 COPY TO 导出完整结果")


if __name__ == "__main__":
    main()
