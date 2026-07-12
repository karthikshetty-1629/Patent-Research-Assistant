"""
Core USPTO patent-grant XML parsing logic.

Consolidates the previously duplicated parsing code (Parser/Validate.py and
patent_parser.py) into a single, reusable module that:
  1. cleans malformed/junk XML content,
  2. extracts a structured patent record suitable for downstream
     parquet conversion and embedding generation.

Structured record fields:
    patent_id, kind, title, filing_date, publication_date, abstract, claims,
    classifications, inventors, applicants, assignees, num_claims
"""
import logging
import re
import xml.etree.ElementTree as ET
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

# Matches a single "<?xml ... ?> ... </us-patent-grant>" document inside a
# larger concatenated dump file.
PATENT_DOCUMENT_PATTERN = re.compile(r"(<\?xml[^>]+\?>.*?</us-patent-grant>)", re.DOTALL)

# Control characters that are illegal in XML 1.0 and occasionally leak into
# USPTO bulk exports.
_CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def clean_malformed_xml(xml_content: str) -> str:
    """Strip illegal control characters and any junk surrounding the root element."""
    xml_content = re.sub(r"^.*?<\?xml", "<?xml", xml_content, flags=re.DOTALL)
    xml_content = re.sub(r"(</us-patent-grant>)\s*<\?xml.*$", r"\1", xml_content, flags=re.DOTALL)
    return _CONTROL_CHARS_PATTERN.sub("", xml_content)


def _text(root: ET.Element, xpath: str) -> Optional[str]:
    node = root.find(xpath)
    return node.text.strip() if node is not None and node.text else None


def parse_patent_xml(xml_content: str) -> Optional[dict]:
    """Parse a single well-formed <us-patent-grant> document into a flat dict."""
    try:
        cleaned = clean_malformed_xml(xml_content)
        root = ET.fromstring(cleaned)
    except ET.ParseError as exc:
        logger.error("Failed to parse patent XML: %s", exc)
        return None

    record = {
        "patent_id": _text(root, ".//doc-number"),
        "kind": _text(root, ".//kind"),
        "title": _text(root, ".//invention-title"),
        "filing_date": _text(root, ".//date-produced") or _text(root, ".//us-application-series-code/../date"),
        "publication_date": _text(root, ".//date-publ") or _text(root, ".//publication-reference//date"),
    }

    abstract_node = root.find(".//abstract")
    record["abstract"] = " ".join(abstract_node.itertext()).strip() if abstract_node is not None else None

    claims = []
    for claim in root.findall(".//claims/claim"):
        claim_text = " ".join(claim.itertext()).strip()
        if claim_text:
            claims.append(claim_text)
    record["claims"] = claims
    record["num_claims"] = len(claims)

    classifications = []
    for classification in root.findall(".//classification-ipcr"):
        main_class = classification.find("main-classification")
        if main_class is not None and main_class.text:
            classifications.append(main_class.text.strip())
    record["classifications"] = classifications

    inventors = []
    for inventor in root.findall(".//inventor") + root.findall(".//us-inventor"):
        first_name = inventor.find(".//first-name")
        last_name = inventor.find(".//last-name")
        if first_name is not None and last_name is not None:
            inventors.append(f"{first_name.text} {last_name.text}".strip())
    record["inventors"] = inventors

    applicants = []
    for applicant in root.findall(".//us-applicant"):
        last_name = applicant.find(".//last-name")
        if last_name is not None and last_name.text:
            applicants.append(last_name.text.strip())
    record["applicants"] = applicants

    assignees = []
    for assignee in root.findall(".//assignee"):
        org_name = assignee.find(".//orgname")
        if org_name is not None and org_name.text:
            assignees.append(org_name.text.strip())
    record["assignees"] = assignees

    return record


def iter_patents_from_dump(content: str) -> Iterator[dict]:
    """Yield structured patent records from a concatenated multi-patent XML dump."""
    for match in PATENT_DOCUMENT_PATTERN.finditer(content):
        record = parse_patent_xml(match.group(1))
        if record is not None:
            yield record


def build_rag_document(record: dict) -> str:
    """Flatten a structured patent record into the text blob used for embedding."""
    parts = [
        record.get("title") or "",
        record.get("abstract") or "",
        " ".join(record.get("claims") or [])[:4000],
    ]
    return "\n\n".join(part for part in parts if part)
