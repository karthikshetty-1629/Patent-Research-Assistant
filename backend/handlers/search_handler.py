"""
API Gateway (HTTP API / Lambda proxy integration) handler for patent search.

Route: POST /search
Body:  {"query": "natural language patent question"}
Response: {"answer": str, "sources": [{"patent_id", "title", "publication_date", "relevance_score"}, ...]}
"""
import json
import logging
from dataclasses import asdict

from backend.rag.chain import PatentRAGChain

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST",
    "Content-Type": "application/json",
}

# Reused across warm invocations of the same Lambda execution environment.
_chain = None


def _get_chain() -> PatentRAGChain:
    global _chain
    if _chain is None:
        _chain = PatentRAGChain()
    return _chain


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "headers": CORS_HEADERS, "body": json.dumps(body)}


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS" or event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return _response(200, {})

    try:
        raw_body = event.get("body") or "{}"
        payload = json.loads(raw_body)
        query = (payload.get("query") or "").strip()
        if not query:
            return _response(400, {"error": "Field 'query' is required."})

        result = _get_chain().answer(query)
        return _response(
            200,
            {
                "answer": result.answer,
                "sources": [asdict(source) for source in result.sources],
            },
        )
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON."})
    except Exception as exc:  # noqa: BLE001 - surfaced to the client as a 500
        logger.exception("Unhandled error in search_handler")
        return _response(500, {"error": str(exc)})
