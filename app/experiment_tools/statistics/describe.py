#!/usr/bin/env python3
import argparse
import os
import sys

import duckdb
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Describe dataset statistics")
    parser.add_argument("file", help="Input file (CSV/JSON/Parquet/Excel)")
    parser.add_argument(
        "--format",
        choices=["auto", "csv", "json", "parquet", "xlsx"],
        default="auto",
        help="File format (default: auto detect)",
    )
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
            query = "SUMMARIZE SELECT * FROM excel_data"
        else:
            if fmt == "csv":
                query = f"SUMMARIZE SELECT * FROM read_csv_auto('{filename}')"
            elif fmt == "json":
                query = f"SUMMARIZE SELECT * FROM read_json_auto('{filename}')"
            elif fmt == "parquet":
                query = f"SUMMARIZE SELECT * FROM read_parquet('{filename}')"
            else:
                print("Unsupported format.")
                sys.exit(1)

        rel = con.sql(query)
        rel.show()
        con.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
