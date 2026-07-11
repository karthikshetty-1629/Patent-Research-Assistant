"""
LLM answer-generation wrapper, defaulting to Falcon-7B-Instruct.

Supports three interchangeable backends selected via LLM_PROVIDER so the
same RAG chain can run against a local/HF-hosted model during development
and a SageMaker real-time endpoint (or Bedrock) in production:

  - "huggingface": HuggingFace Hub Inference API (tiiuae/falcon-7b-instruct)
  - "sagemaker":   A deployed SageMaker real-time inference endpoint
  - "bedrock":     Amazon Bedrock text-generation model
"""
import json
import logging

import boto3

from backend.config import config

logger = logging.getLogger(__name__)


class PatentLLM:
    """Generates a grounded answer from a prompt built out of retrieved patent context."""

    def __init__(self, provider: str | None = None):
        self.provider = provider or config.LLM_PROVIDER

    def generate(self, prompt: str) -> str:
        if self.provider == "sagemaker":
            return self._generate_sagemaker(prompt)
        if self.provider == "bedrock":
            return self._generate_bedrock(prompt)
        return self._generate_huggingface(prompt)

    # -- HuggingFace Hub Inference API -----------------------------------
    def _generate_huggingface(self, prompt: str) -> str:
        from huggingface_hub import InferenceClient

        client = InferenceClient(model=config.LLM_MODEL_NAME, token=config.HUGGINGFACEHUB_API_TOKEN or None)
        response = client.text_generation(
            prompt,
            max_new_tokens=config.LLM_MAX_NEW_TOKENS,
            temperature=max(config.LLM_TEMPERATURE, 0.01),
        )
        return response.strip()

    # -- SageMaker real-time endpoint ------------------------------------
    def _generate_sagemaker(self, prompt: str) -> str:
        runtime = boto3.client("sagemaker-runtime", region_name=config.AWS_REGION)
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": config.LLM_MAX_NEW_TOKENS,
                "temperature": max(config.LLM_TEMPERATURE, 0.01),
                "return_full_text": False,
            },
        }
        response = runtime.invoke_endpoint(
            EndpointName=config.SAGEMAKER_ENDPOINT_NAME,
            ContentType="application/json",
            Body=json.dumps(payload),
        )
        body = json.loads(response["Body"].read().decode("utf-8"))
        if isinstance(body, list):
            return body[0].get("generated_text", "").strip()
        return body.get("generated_text", "").strip()

    # -- Amazon Bedrock -----------------------------------------------------
    def _generate_bedrock(self, prompt: str) -> str:
        bedrock = boto3.client("bedrock-runtime", region_name=config.AWS_REGION)
        payload = {
            "prompt": prompt,
            "max_tokens": config.LLM_MAX_NEW_TOKENS,
            "temperature": config.LLM_TEMPERATURE,
        }
        response = bedrock.invoke_model(
            modelId=config.LLM_MODEL_NAME,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )
        body = json.loads(response["body"].read())
        return body.get("completion", body.get("outputText", "")).strip()
