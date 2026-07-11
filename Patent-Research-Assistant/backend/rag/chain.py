"""
End-to-end RAG chain: embed query -> retrieve top-k patents from OpenSearch
-> build a grounded prompt -> generate an answer with citations.

This is the module invoked directly by the search Lambda (backend/lambda/
search_handler.py) and by any local/CLI usage.
"""
import logging
from dataclasses import dataclass, field

from backend.config import config
from backend.rag.embeddings import PatentEmbedder
from backend.rag.llm import PatentLLM
from backend.rag.retriever import PatentOpenSearchRetriever

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """You are a patent research assistant. Answer the user's question using ONLY the
patent excerpts provided below. Cite patent numbers in your answer. If the excerpts do not contain
enough information to answer, say so explicitly instead of guessing.

Patent excerpts:
{context}

Question: {question}

Answer:"""


@dataclass
class Source:
    patent_id: str
    title: str | None
    publication_date: str | None
    relevance_score: float | None


@dataclass
class RAGResult:
    answer: str
    sources: list[Source] = field(default_factory=list)


class PatentRAGChain:
    def __init__(self, retriever: PatentOpenSearchRetriever | None = None, llm: PatentLLM | None = None):
        self.retriever = retriever or PatentOpenSearchRetriever(embedder=PatentEmbedder())
        self.llm = llm or PatentLLM()

    def _build_context(self, documents) -> str:
        blocks = []
        for doc in documents:
            patent_id = doc.metadata.get("patent_id", "unknown")
            blocks.append(f"[Patent {patent_id}] {doc.page_content[:1500]}")
        return "\n\n---\n\n".join(blocks)

    def answer(self, question: str) -> RAGResult:
        documents = self.retriever.invoke(question)
        if not documents:
            return RAGResult(answer="No relevant patents were found for this query.", sources=[])

        context = self._build_context(documents)
        prompt = PROMPT_TEMPLATE.format(context=context, question=question)
        answer_text = self.llm.generate(prompt)

        sources = [
            Source(
                patent_id=doc.metadata.get("patent_id"),
                title=doc.metadata.get("title"),
                publication_date=doc.metadata.get("publication_date"),
                relevance_score=doc.metadata.get("relevance_score"),
            )
            for doc in documents
        ]
        return RAGResult(answer=answer_text, sources=sources)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    query = " ".join(sys.argv[1:]) or "What patents relate to lithium-ion battery thermal management?"
    chain = PatentRAGChain()
    result = chain.answer(query)
    print(f"\nAnswer:\n{result.answer}\n")
    print("Sources:")
    for source in result.sources:
        print(f"  - {source.patent_id}: {source.title} ({source.publication_date}) score={source.relevance_score}")
