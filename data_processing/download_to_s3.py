"""
Download USPTO bulk full-text patent grant data and upload it to S3.

Replaces the ad-hoc year-by-year notebooks (notebooks/uploading_files_*.ipynb)
with a single, parameterized, resumable CLI script.

Usage:
    python -m data_processing.download_to_s3 --start-year 1976 --end-year 2000 \
        --bucket patent-research-assistant --prefix uspto/fulltext

    python -m data_processing.download_to_s3 --start-year 1971 --end-year 1975 \
        --bucket patent-research-assistant --dry-run
"""
import argparse
import logging
import re
import sys
from dataclasses import dataclass
from typing import Iterator

import boto3
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://bulkdata.uspto.gov/data/patent/grant/redbook/fulltext/"
ZIP_PATTERN = re.compile(r"US_PATFT_BRS_Full_Text_Extract_\d+_\d+\.zip$")
DOC_PATTERN = re.compile(r"US_PATFT_BRS_form\.doc$")
XML_ZIP_PATTERN = re.compile(r"ipg\d{6}\.zip$")


@dataclass
class RemoteFile:
    year: int
    file_name: str
    url: str


def discover_year_files(year: int, session: requests.Session) -> Iterator[RemoteFile]:
    """List downloadable files for a given year's bulk-data directory."""
    year_url = f"{BASE_URL}{year}/"
    logger.info("Listing %s", year_url)
    try:
        response = session.get(year_url, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to access %s: %s", year_url, exc)
        return

    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.find_all("a", href=True):
        file_name = link["href"]
        if ZIP_PATTERN.match(file_name) or DOC_PATTERN.match(file_name) or XML_ZIP_PATTERN.match(file_name):
            yield RemoteFile(year=year, file_name=file_name, url=year_url + file_name)


def stream_upload(remote_file: RemoteFile, bucket: str, prefix: str, s3_client, session: requests.Session) -> None:
    s3_key = f"{prefix}/{remote_file.year}/{remote_file.file_name}"
    logger.info("Downloading %s", remote_file.url)
    with session.get(remote_file.url, stream=True, timeout=60) as file_response:
        file_response.raise_for_status()
        logger.info("Uploading to s3://%s/%s", bucket, s3_key)
        s3_client.upload_fileobj(file_response.raw, bucket, s3_key)
    logger.info("Done: s3://%s/%s", bucket, s3_key)


def run(start_year: int, end_year: int, bucket: str, prefix: str, dry_run: bool = False) -> None:
    session = requests.Session()
    s3_client = None if dry_run else boto3.client("s3")

    total = 0
    for year in range(start_year, end_year + 1):
        for remote_file in discover_year_files(year, session):
            total += 1
            if dry_run:
                logger.info("[dry-run] would upload %s -> s3://%s/%s/%s/%s",
                            remote_file.url, bucket, prefix, remote_file.year, remote_file.file_name)
                continue
            try:
                stream_upload(remote_file, bucket, prefix, s3_client, session)
            except (requests.exceptions.RequestException, boto3.exceptions.Boto3Error) as exc:
                logger.error("Failed on %s: %s", remote_file.file_name, exc)

    logger.info("Processed %d file(s) for years %d-%d", total, start_year, end_year)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--bucket", type=str, required=True, help="Destination S3 bucket name")
    parser.add_argument("--prefix", type=str, default="uspto/fulltext", help="S3 key prefix")
    parser.add_argument("--dry-run", action="store_true", help="List files without downloading/uploading")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    if args.start_year > args.end_year:
        logger.error("--start-year must be <= --end-year")
        return 1
    run(args.start_year, args.end_year, args.bucket, args.prefix, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
