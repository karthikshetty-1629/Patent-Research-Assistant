"""
Read parsed patent Parquet files, generate PatentSBERTa embeddings, and
bulk-index the resulting documents into OpenSearch for k-NN retrieval.

This is the final stage of the offline pipeline:
    download_to_s3 -> xml_splitter -> xml_validator -> xml_to_parquet -> build_embeddings

Usage:
    python -m data_processing.build_embeddings --parquet-dir /data/parquet
"""
import argparse
import glob
import logging
import sys

import pandas as pd

from backend.config import config
from backend.rag.embeddings import PatentEmbedder
from backend.rag.opensearch_client import bulk_index_patents, ensure_index, get_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _build_text_for_embedding(row: pd.Series) -> str:
    claims_preview = " ".join(row.get("claims") or [])[:2000]
    return "\n\n".join(filter(None, [row.get("title"), row.get("abstract"), claims_preview]))


def process_parquet_dir(parquet_dir: str, batch_size: int = 64, dry_run: bool = False) -> int:
    embedder = PatentEmbedder()
    client = None if dry_run else get_client()
    if not dry_run:
        ensure_index(client)

    total = 0
    part_files = sorted(glob.glob(f"{parquet_dir}/*.parquet"))
    if not part_files:
        logger.warning("No parquet files found under %s", parquet_dir)
        return 0

    for part_file in part_files:
        df = pd.read_parquet(part_file)
        logger.info("Embedding %d record(s) from %s", len(df), part_file)

        for start in range(0, len(df), batch_size):
            batch_df = df.iloc[start:start + batch_size]
            texts = [_build_text_for_embedding(row) for _, row in batch_df.iterrows()]
            embeddings = embedder.embed_documents(texts)

            docs = []
            for (_, row), embedding in zip(batch_df.iterrows(), embeddings):
                docs.append(
                    {
                        "patent_id": row.get("patent_id"),
                        "title": row.get("title"),
                        "abstract": row.get("abstract"),
                        "claims_preview": " ".join(row.get("claims") or [])[:2000],
                        "inventors": list(row.get("inventors") or []),
                        "assignees": list(row.get("assignees") or []),
                        "classifications": list(row.get("classifications") or []),
                        "publication_date": row.get("publication_date"),
                        "embedding": embedding,
                    }
                )

            if dry_run:
                logger.info("[dry-run] would index %d document(s)", len(docs))
            else:
                bulk_index_patents(client, docs)
            total += len(docs)

    return total


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--parquet-dir", required=True, help="Directory of .parquet part files to embed and index")
    parser.add_argument("--batch-size", type=int, default=64, help="Embedding batch size")
    parser.add_argument("--dry-run", action="store_true", help="Compute embeddings but skip OpenSearch indexing")
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    total = process_parquet_dir(args.parquet_dir, args.batch_size, args.dry_run)
    logger.info("Indexed %d patent document(s) into '%s'", total, config.OPENSEARCH_INDEX)
    return 0


if __name__ == "__main__":
    sys.exit(main())
