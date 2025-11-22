#!/usr/bin/env python3
import argparse
import os
import sys

import duckdb
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Show head of dataset")
    parser.add_argument("file", help="Input file (CSV/JSON/Parquet/Excel)")
    parser.add_argument(
        "--format",
        choices=["auto", "csv", "json", "parquet", "xlsx"],
        default="auto",
        help="File format (default: auto detect)",
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of rows to show (default: 10)")
    args = parser.parse_args()

    filename = args.file
    if not os.path.exists(filename):
        print(f"❌ File '{filename}' not found.")
        sys.exit(1)

    fmt = args.format
    if fmt == "auto":
        if filename.endswith((".json", ".jsonl")):
            fmt = "json"
        elif filename.endswith(".parquet"):
            fmt = "parquet"
        elif filename.endswith((".xlsx", ".xls")):
            fmt = "xlsx"
        else:
            fmt = "csv"

    try:
        con = duckdb.connect()

        # Handle Excel files separately using pandas
        if fmt == "xlsx":
            df = pd.read_excel(filename)
            # Register the dataframe as a DuckDB table
            con.register("excel_data", df)
            query = f"SELECT * FROM excel_data LIMIT {args.limit}"
        else:
            if fmt == "csv":
                read_func = "read_csv_auto"
            elif fmt == "json":
                read_func = "read_json_auto"
            elif fmt == "parquet":
                read_func = "read_parquet"
            else:
                print("Unsupported format.")
                sys.exit(1)

            query = f"SELECT * FROM {read_func}('{filename}') LIMIT {args.limit}"

        rel = con.sql(query)
        rel.show()
        con.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
