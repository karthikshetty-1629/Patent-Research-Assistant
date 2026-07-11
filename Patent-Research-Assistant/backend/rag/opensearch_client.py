"""
AWS OpenSearch client with k-NN vector search support.

Handles IAM-signed requests (SigV4) against an OpenSearch Service domain so
Lambda execution roles can authenticate without static credentials, and
falls back to basic auth for local/dev clusters.
"""
import logging
from typing import Any

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection

from backend.config import config

logger = logging.getLogger(__name__)

INDEX_MAPPING = {
    "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 100}},
    "mappings": {
        "properties": {
            "patent_id": {"type": "keyword"},
            "title": {"type": "text"},
            "abstract": {"type": "text"},
            "claims_preview": {"type": "text"},
            "inventors": {"type": "keyword"},
            "assignees": {"type": "keyword"},
            "classifications": {"type": "keyword"},
            "publication_date": {"type": "keyword"},
            "embedding": {
                "type": "knn_vector",
                "dimension": config.EMBEDDING_DIMENSIONS,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {"ef_construction": 128, "m": 24},
                },
            },
        }
    },
}


def get_client() -> OpenSearch:
    host = config.OPENSEARCH_ENDPOINT.replace("https://", "").replace("http://", "")
    if not host:
        raise RuntimeError("OPENSEARCH_ENDPOINT is not configured")

    if config.OPENSEARCH_USE_IAM_AUTH:
        session = boto3.Session()
        credentials = session.get_credentials()
        auth = AWSV4SignerAuth(credentials, config.AWS_REGION, "es")
    else:
        import os

        auth = (os.environ.get("OPENSEARCH_USER", "admin"), os.environ.get("OPENSEARCH_PASSWORD", "admin"))

    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
    )


def ensure_index(client: OpenSearch, index_name: str | None = None) -> None:
    index_name = index_name or config.OPENSEARCH_INDEX
    if client.indices.exists(index=index_name):
        return
    logger.info("Creating OpenSearch index '%s'", index_name)
    client.indices.create(index=index_name, body=INDEX_MAPPING)


def bulk_index_patents(client: OpenSearch, patent_docs: list[dict[str, Any]], index_name: str | None = None) -> None:
    """Bulk-index a batch of documents shaped like {patent_id, title, abstract, embedding, ...}."""
    from opensearchpy.helpers import bulk

    index_name = index_name or config.OPENSEARCH_INDEX
    actions = [
        {
            "_index": index_name,
            "_id": doc["patent_id"],
            "_source": doc,
        }
        for doc in patent_docs
        if doc.get("patent_id")
    ]
    if not actions:
        return
    success, errors = bulk(client, actions, raise_on_error=False)
    logger.info("Bulk indexed %d document(s), %d error(s)", success, len(errors) if errors else 0)


def knn_search(client: OpenSearch, query_embedding: list[float], top_k: int | None = None,
                index_name: str | None = None) -> list[dict[str, Any]]:
    index_name = index_name or config.OPENSEARCH_INDEX
    top_k = top_k or config.RETRIEVAL_TOP_K

    query = {
        "size": top_k,
        "query": {"knn": {"embedding": {"vector": query_embedding, "k": top_k}}},
    }
    response = client.search(index=index_name, body=query)
    hits = response.get("hits", {}).get("hits", [])
    results = []
    for hit in hits:
        source = hit["_source"]
        source["_score"] = hit["_score"]
        results.append(source)
    return results
