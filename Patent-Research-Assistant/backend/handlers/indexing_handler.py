"""
S3-triggered Lambda: fires whenever a new raw USPTO XML dump lands under
s3://<bucket>/uspto/fulltext/**, and turns it into searchable embeddings.

This is the event-driven equivalent of the offline
data_processing.build_embeddings batch script, so patents become
searchable within seconds of being uploaded instead of waiting on a
scheduled batch job.

Configure via S3 -> Properties -> Event notifications -> "All object
create events" filtered to the raw XML prefix, targeting this function.
"""
import logging
import urllib.parse

import boto3

from backend.config import config
from backend.rag.embeddings import PatentEmbedder
from backend.rag.opensearch_client import bulk_index_patents, ensure_index, get_client
from data_processing.xml_parser import iter_patents_from_dump

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

s3_client = boto3.client("s3")

_embedder = None
_opensearch_client = None


def _get_embedder() -> PatentEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = PatentEmbedder()
    return _embedder


def _get_opensearch_client():
    global _opensearch_client
    if _opensearch_client is None:
        _opensearch_client = get_client()
        ensure_index(_opensearch_client)
    return _opensearch_client


def _build_text_for_embedding(record: dict) -> str:
    claims_preview = " ".join(record.get("claims") or [])[:2000]
    return "\n\n".join(filter(None, [record.get("title"), record.get("abstract"), claims_preview]))


def _index_records(records: list[dict]) -> int:
    if not records:
        return 0

    embedder = _get_embedder()
    texts = [_build_text_for_embedding(record) for record in records]
    embeddings = embedder.embed_documents(texts)

    docs = []
    for record, embedding in zip(records, embeddings):
        docs.append(
            {
                "patent_id": record.get("patent_id"),
                "title": record.get("title"),
                "abstract": record.get("abstract"),
                "claims_preview": " ".join(record.get("claims") or [])[:2000],
                "inventors": record.get("inventors") or [],
                "assignees": record.get("assignees") or [],
                "classifications": record.get("classifications") or [],
                "publication_date": record.get("publication_date"),
                "embedding": embedding,
            }
        )

    client = _get_opensearch_client()
    bulk_index_patents(client, docs)
    return len(docs)


def handler(event, context):
    total_indexed = 0
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(record["s3"]["object"]["key"])
        logger.info("Processing s3://%s/%s", bucket, key)

        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response["Body"].read().decode("utf-8", errors="replace")

        patent_records = list(iter_patents_from_dump(content))
        logger.info("Parsed %d patent document(s) from %s", len(patent_records), key)

        # Index in bounded batches to keep memory/latency predictable.
        batch_size = config.EMBEDDING_BATCH_SIZE
        for start in range(0, len(patent_records), batch_size):
            batch = patent_records[start:start + batch_size]
            total_indexed += _index_records(batch)

    return {"statusCode": 200, "indexed": total_indexed}
