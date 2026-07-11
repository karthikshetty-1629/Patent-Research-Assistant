"""
Convert validated, split USPTO patent XML documents into partitioned Parquet
files using the structured schema from data_processing.xml_parser.

Usage:
    python -m data_processing.xml_to_parquet --input-dir /data/split --output-dir /data/parquet
    python -m data_processing.xml_to_parquet --input-dir /data/split --output-dir /data/parquet \
        --batch-size 5000 --single-file
"""
import argparse
import logging
import os
import sys

import pandas as pd

from data_processing.xml_parser import parse_patent_xml

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _iter_records(input_dir: str):
    for file_name in sorted(os.listdir(input_dir)):
        if not file_name.endswith(".xml"):
            continue
        file_path = os.path.join(input_dir, file_name)
        with open(file_path, "r", encoding="utf-8", errors="replace") as file_obj:
            content = file_obj.read()
        record = parse_patent_xml(content)
        if record is None:
            logger.warning("Skipping unparseable file: %s", file_name)
            continue
        record["source_file"] = file_name
        yield record


def convert(input_dir: str, output_dir: str, batch_size: int = 2000, single_file: bool = False) -> int:
    os.makedirs(output_dir, exist_ok=True)

    batch: list[dict] = []
    total = 0
    part = 0

    def flush(current_batch: list[dict], part_index: int) -> None:
        if not current_batch:
            return
        df = pd.DataFrame(current_batch)
        # Arrow can't infer a type for list-typed columns full of empty lists;
        # stringify claims/classification lists rather than losing the column.
        for col in ("claims", "classifications", "inventors", "applicants", "assignees"):
            if col in df.columns:
                df[col] = df[col].apply(lambda value: value if isinstance(value, list) else [])
        out_path = os.path.join(output_dir, f"part_{part_index:05d}.parquet")
        df.to_parquet(out_path, engine="pyarrow", index=False)
        logger.info("Wrote %d records to %s", len(current_batch), out_path)

    all_records: list[dict] = []
    for record in _iter_records(input_dir):
        batch.append(record)
        total += 1
        if not single_file and len(batch) >= batch_size:
            flush(batch, part)
            part += 1
            batch = []
        elif single_file:
            all_records.append(record)

    if single_file:
        flush(all_records, 0)
    else:
        flush(batch, part)

    return total


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", required=True, help="Directory of validated, split .xml documents")
    parser.add_argument("--output-dir", required=True, help="Directory to write .parquet part files to")
    parser.add_argument("--batch-size", type=int, default=2000, help="Records per parquet part file")
    parser.add_argument("--single-file", action="store_true", help="Write a single consolidated parquet file")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    total = convert(args.input_dir, args.output_dir, args.batch_size, args.single_file)
    logger.info("Converted %d patent record(s) into %s", total, args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
