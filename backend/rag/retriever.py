"""
LangChain-compatible retriever backed by the OpenSearch k-NN index.

Wraps embeddings.PatentEmbedder + opensearch_client.knn_search behind the
standard LangChain BaseRetriever interface so it can be dropped into any
LangChain chain, agent, or evaluation harness.
"""
from typing import Any

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from backend.config import config
from backend.rag.embeddings import PatentEmbedder
from backend.rag.opensearch_client import get_client, knn_search


class PatentOpenSearchRetriever(BaseRetriever):
    """Retrieves the top-k most semantically similar patents for a query."""

    embedder: Any = None
    top_k: int = config.RETRIEVAL_TOP_K

    def __init__(self, embedder: PatentEmbedder | None = None, top_k: int | None = None, **kwargs):
        super().__init__(**kwargs)
        self.embedder = embedder or PatentEmbedder()
        self.top_k = top_k or config.RETRIEVAL_TOP_K

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        query_embedding = self.embedder.embed_query(query)
        client = get_client()
        hits = knn_search(client, query_embedding, top_k=self.top_k)

        documents = []
        for hit in hits:
            content = "\n\n".join(filter(None, [hit.get("title"), hit.get("abstract"), hit.get("claims_preview")]))
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "patent_id": hit.get("patent_id"),
                        "title": hit.get("title"),
                        "publication_date": hit.get("publication_date"),
                        "inventors": hit.get("inventors"),
                        "assignees": hit.get("assignees"),
                        "classifications": hit.get("classifications"),
                        "relevance_score": hit.get("_score"),
                    },
                )
            )
        return documents

    async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> list[Document]:
        # OpenSearch client here is synchronous; run in the default executor.
        import asyncio

        return await asyncio.get_event_loop().run_in_executor(None, self._get_relevant_documents, query)
