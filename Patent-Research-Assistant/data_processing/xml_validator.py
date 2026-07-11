"""
Validate that split XML documents are well-formed before they enter the
parquet / embedding stages of the pipeline.

Usage:
    python -m data_processing.xml_validator --input-dir /data/split
"""
import argparse
import logging
import os
import sys
import xml.etree.ElementTree as ET

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def validate_directory(input_dir: str) -> tuple[int, int]:
    """Validate every .xml file in a directory. Returns (valid_count, invalid_count)."""
    valid, invalid = 0, 0
    for file_name in sorted(os.listdir(input_dir)):
        if not file_name.endswith(".xml"):
            continue
        file_path = os.path.join(input_dir, file_name)
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            logger.info("%s is valid (root=%s)", file_name, root.tag)
            valid += 1
        except ET.ParseError as exc:
            logger.error("%s is INVALID: %s", file_name, exc)
            invalid += 1
    return valid, invalid


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input-dir", required=True, help="Directory of split .xml documents to validate")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    valid, invalid = validate_directory(args.input_dir)
    logger.info("Validation complete: %d valid, %d invalid", valid, invalid)
    return 1 if invalid else 0


if __name__ == "__main__":
    sys.exit(main())
