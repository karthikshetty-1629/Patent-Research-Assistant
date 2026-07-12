"""
Patent-domain sentence embeddings via PatentSBERTa.

PatentSBERTa (AI-Growth-Lab/PatentSBERTa) is a Sentence-BERT model
fine-tuned on patent claims/abstracts and produces 768-dimensional
embeddings, giving much better semantic separation between patent
documents than a general-purpose embedding model.

The model is loaded lazily and cached at module scope so that repeated
Lambda invocations on a warm container reuse the same in-memory model.
"""
import logging
import threading
from typing import Sequence

from backend.config import config

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model: %s", config.EMBEDDING_MODEL_NAME)
                _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _model


class PatentEmbedder:
    """Thin wrapper around a SentenceTransformer model for patent text."""

    def __init__(self, model_name: str | None = None, batch_size: int | None = None):
        self.model_name = model_name or config.EMBEDDING_MODEL_NAME
        self.batch_size = batch_size or config.EMBEDDING_BATCH_SIZE
        self._model = _get_model() if self.model_name == config.EMBEDDING_MODEL_NAME else None

    def _resolve_model(self):
        if self._model is not None:
            return self._model
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        model = self._resolve_model()
        embeddings = model.encode(
            list(texts),
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


# LangChain-compatible thin adapter, so PatentEmbedder can be passed directly
# to LangChain vector store integrations if desired.
class LangChainPatentEmbeddings:
    def __init__(self, embedder: PatentEmbedder | None = None):
        self.embedder = embedder or PatentEmbedder()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embedder.embed_query(text)
