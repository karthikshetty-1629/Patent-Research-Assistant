"""
Small utility for inspecting a parquet file or directory produced by
xml_to_parquet.py.

Usage:
    python -m data_processing.view_parquet --path /data/parquet/part_00000.parquet
    python -m data_processing.view_parquet --path /data/parquet --rows 10
"""
import argparse
import sys

import pandas as pd


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--path", required=True, help="Path to a .parquet file or a directory of part files")
    parser.add_argument("--rows", type=int, default=5, help="Number of rows to preview")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    df = pd.read_parquet(args.path)
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}\n")
    print(df.head(args.rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
