"""
DuckDB 数据查询工具
用法: python data_query.py "SELECT * FROM 'data.csv'"

支持格式:
- CSV/JSON/Parquet: 直接由 DuckDB 读取
- Excel (xlsx/xls): 由 Polars 预处理后注册到 DuckDB
"""

import re
import sys
from pathlib import Path

import duckdb
import polars as pl


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

        # 预处理 Excel 文件并注册到 DuckDB（返回修改后的查询）
        query = register_excel_files(con, query)

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


def register_excel_files(con: duckdb.DuckDBPyConnection, query: str) -> str:
    """使用 Polars 预处理 Excel 文件并注册到 DuckDB

    Returns:
        修改后的查询语句（将 Excel 文件路径替换为表名）
    """
    # 匹配 Excel 文件路径
    pattern = r"['\"]([^'\"]+\.(xlsx|xls))['\"]"
    excel_files = re.findall(pattern, query, re.IGNORECASE)

    modified_query = query

    for file_path, _ in excel_files:
        # 跳过通配符
        if "*" in file_path or "?" in file_path:
            continue

        if not Path(file_path).exists():
            continue

        try:
            # 使用 Polars 读取 Excel 文件
            print(f"📊 使用 Polars 预处理: {file_path}")
            df_polars = pl.read_excel(file_path)

            # 转换为 Pandas DataFrame (DuckDB 兼容性更好)
            df_pandas = df_polars.to_pandas()

            # 生成表名 (移除路径和扩展名)
            table_name = Path(file_path).stem

            # 注册到 DuckDB
            con.register(table_name, df_pandas)
            print(f"✅ 已注册表: {table_name} ({len(df_pandas)} 行 × {len(df_pandas.columns)} 列)\n")

            # 替换查询中的文件路径为表名
            # 匹配带引号的文件路径
            modified_query = re.sub(
                rf"['\"]({re.escape(file_path)})['\"]",
                table_name,
                modified_query,
                flags=re.IGNORECASE,
            )

        except Exception as e:
            print(f"⚠️  预处理 {file_path} 失败: {e}", file=sys.stderr)
            continue

    return modified_query


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
