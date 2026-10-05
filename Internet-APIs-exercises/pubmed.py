"""Studio 4, Exercise 1: retrieve PubMed XML with requests."""

import argparse
from pathlib import Path
import xml.etree.ElementTree as ET

import requests


EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def get_pubmed_data(pmid):
    """Return raw XML for one PMID; propagate network/HTTP errors to the caller.

    This retrieval function does not interpret the XML. A successful HTTP
    response does not by itself guarantee a matching record or an abstract.
    Callers making repeated requests must enforce NCBI's rate limit.
    """
    pmid = str(pmid).strip()
    if not pmid.isascii() or not pmid.isdigit() or int(pmid) <= 0:
        raise ValueError("pmid must be a positive integer identifier")
    response = requests.get(
        EFETCH_URL,
        params={"db": "pubmed", "id": pmid, "retmode": "xml",
                "tool": "bis634_studio4"},
        headers={"User-Agent": "bis634-studio4/0.1"},
        timeout=30,
    )
    response.raise_for_status()
    # Decode the XML bytes explicitly rather than trusting a guessed HTTP encoding.
    return response.content.decode("utf-8")


def extract_abstract(xml_payload):
    """Extract the primary abstract from a single-record PubMed XML payload.

    Preserve section order, labels, and inline text. Return an empty string
    when no abstract exists. Malformed XML raises ET.ParseError; multi-record
    payloads raise ValueError rather than silently mixing different papers.
    """
    root = ET.fromstring(xml_payload)
    records = root.findall("./PubmedArticle") + root.findall("./PubmedBookArticle")
    if len(records) > 1:
        raise ValueError("extract_abstract expects at most one PubMed record")
    sections = root.findall("./PubmedArticle/MedlineCitation/Article/Abstract/AbstractText")
    sections += root.findall("./PubmedBookArticle/BookDocument/Abstract/AbstractText")
    paragraphs = []
    for section in sections:
        # .text alone loses text inside nested tags and their following tails.
        text = "".join(section.itertext()).strip()
        label = section.get("Label", "").strip()
        if text:
            paragraphs.append(f"{label}: {text}" if label else text)
    return "\n\n".join(paragraphs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pmid")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    xml_payload = get_pubmed_data(args.pmid)
    args.output.write_text(xml_payload, encoding="utf-8")
    print(f"Saved PMID {args.pmid}: {len(xml_payload)} characters to {args.output}")
