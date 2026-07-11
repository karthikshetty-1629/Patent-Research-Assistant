"""
Split a concatenated USPTO bulk XML file (e.g. ipg231226.xml, which contains
thousands of back-to-back <us-patent-grant> documents in one file) into
individual, well-formed XML documents.

Usage:
    python -m data_processing.xml_splitter --input /data/raw/ipg231226.xml --output-dir /data/split

    python -m data_processing.xml_splitter --input s3://my-bucket/uspto/ipg231226.xml \
        --output-dir /data/split
"""
import argparse
import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

XML_DECLARATION = '<?xml version="1.0" encoding="UTF-8"?>'


def _read_source(path: str) -> str:
    if path.startswith("s3://"):
        import boto3

        bucket, key = path[len("s3://"):].split("/", 1)
        s3_client = boto3.client("s3")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8", errors="replace")

    with open(path, "r", encoding="utf-8", errors="replace") as file_obj:
        return file_obj.read()


def split_concatenated_xml(content: str, output_dir: str, file_prefix: str = "document") -> int:
    """Split on XML declarations and write one file per patent document."""
    os.makedirs(output_dir, exist_ok=True)

    documents = content.split(XML_DECLARATION)
    written = 0
    for i, document in enumerate(documents):
        stripped = document.strip()
        if not stripped:
            continue
        doc_content = f"{XML_DECLARATION}\n{stripped}"
        output_path = os.path.join(output_dir, f"{file_prefix}_{i + 1}.xml")
        with open(output_path, "w", encoding="utf-8") as out_file:
            out_file.write(doc_content)
        written += 1

    return written


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, help="Local path or s3:// URI to the concatenated XML file")
    parser.add_argument("--output-dir", required=True, help="Directory to write individual XML documents to")
    parser.add_argument("--prefix", default="document", help="Filename prefix for split documents")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    content = _read_source(args.input)
    count = split_concatenated_xml(content, args.output_dir, args.prefix)
    logger.info("Split %d document(s) into %s", count, args.output_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
