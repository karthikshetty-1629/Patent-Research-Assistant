"""
Centralized environment-driven configuration for the backend.

All values are read from environment variables (populated via .env locally,
or via Lambda environment variables in AWS) so the same code runs
identically in a notebook, a container, and a deployed Lambda function.
"""
import os

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


class Config:
    # --- AWS ---
    AWS_REGION: str = _env("AWS_REGION", "us-east-1")
    S3_BUCKET: str = _env("S3_BUCKET", "patent-research-assistant")
    S3_RAW_PREFIX: str = _env("S3_RAW_PREFIX", "uspto/fulltext")

    # --- OpenSearch (vector store) ---
    OPENSEARCH_ENDPOINT: str = _env("OPENSEARCH_ENDPOINT", "")
    OPENSEARCH_INDEX: str = _env("OPENSEARCH_INDEX", "patents")
    OPENSEARCH_USE_IAM_AUTH: bool = _env("OPENSEARCH_USE_IAM_AUTH", "true").lower() == "true"

    # --- Embeddings ---
    EMBEDDING_MODEL_NAME: str = _env("EMBEDDING_MODEL_NAME", "AI-Growth-Lab/PatentSBERTa")
    EMBEDDING_DIMENSIONS: int = int(_env("EMBEDDING_DIMENSIONS", "768"))
    EMBEDDING_BATCH_SIZE: int = int(_env("EMBEDDING_BATCH_SIZE", "32"))

    # --- LLM (generation) ---
    LLM_PROVIDER: str = _env("LLM_PROVIDER", "huggingface")  # huggingface | sagemaker | bedrock
    LLM_MODEL_NAME: str = _env("LLM_MODEL_NAME", "tiiuae/falcon-7b-instruct")
    SAGEMAKER_ENDPOINT_NAME: str = _env("SAGEMAKER_ENDPOINT_NAME", "")
    HUGGINGFACEHUB_API_TOKEN: str = _env("HUGGINGFACEHUB_API_TOKEN", "")
    LLM_MAX_NEW_TOKENS: int = int(_env("LLM_MAX_NEW_TOKENS", "512"))
    LLM_TEMPERATURE: float = float(_env("LLM_TEMPERATURE", "0.2"))

    # --- Retrieval / RAG ---
    RETRIEVAL_TOP_K: int = int(_env("RETRIEVAL_TOP_K", "5"))

    # --- Auth ---
    COGNITO_USER_POOL_ID: str = _env("COGNITO_USER_POOL_ID", "")
    COGNITO_APP_CLIENT_ID: str = _env("COGNITO_APP_CLIENT_ID", "")


config = Config()
