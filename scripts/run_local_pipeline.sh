#!/usr/bin/env bash
# Runs the full offline pipeline end-to-end against a local directory of
# raw USPTO bulk XML dumps:
#
#   raw XML dump -> split -> validate -> parquet -> embeddings -> OpenSearch
#
# Usage:
#   ./scripts/run_local_pipeline.sh /path/to/ipg231226.xml ./data
set -euo pipefail

RAW_XML_FILE="${1:?Usage: run_local_pipeline.sh <raw-xml-file> <working-dir>}"
WORK_DIR="${2:?Usage: run_local_pipeline.sh <raw-xml-file> <working-dir>}"

SPLIT_DIR="${WORK_DIR}/split"
PARQUET_DIR="${WORK_DIR}/parquet"

echo "==> 1/4 Splitting concatenated XML dump"
python -m data_processing.xml_splitter --input "${RAW_XML_FILE}" --output-dir "${SPLIT_DIR}"

echo "==> 2/4 Validating split documents"
python -m data_processing.xml_validator --input-dir "${SPLIT_DIR}"

echo "==> 3/4 Converting to Parquet"
python -m data_processing.xml_to_parquet --input-dir "${SPLIT_DIR}" --output-dir "${PARQUET_DIR}"

echo "==> 4/4 Generating embeddings and indexing into OpenSearch"
python -m data_processing.build_embeddings --parquet-dir "${PARQUET_DIR}"

echo "Pipeline complete. Query it with: python -m backend.rag.chain \"your question here\""
