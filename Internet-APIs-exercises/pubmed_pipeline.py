"""Fetch the assigned records and check their abstracts for two terms."""

import argparse
import csv
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from pubmed import extract_abstract, get_pubmed_data


PMID_LIST = [34807729, 21943025, 33980688, 32299786, 20725509,
             41916485, 17245822, 31842501, 35064122]
FIELDS = ["PMID", "Status", "chemokines", "COVID-19", "Details"]


def inspect_record(pmid, xml_payload):
    """Check record identity before looking for terms in its abstract."""
    row = dict(zip(FIELDS, [str(pmid), "", "N/A", "N/A", ""]))
    root = ET.fromstring(xml_payload)
    error = root.find(".//ERROR")
    if error is not None:
        row.update(Status="API error", Details="".join(error.itertext()).strip())
        return row
    if root.tag != "PubmedArticleSet":
        row.update(Status="Unexpected XML", Details=f"Root element: {root.tag}")
        return row
    ids = root.findall("./PubmedArticle/MedlineCitation/PMID")
    ids += root.findall("./PubmedBookArticle/BookDocument/PMID")
    if not ids:
        row.update(Status="No record", Details="No PubMed record returned")
        return row
    if len(ids) != 1 or ids[0].text != str(pmid):
        row.update(Status="Record mismatch", Details="Returned PMID does not match the request")
        return row

    abstract = extract_abstract(xml_payload)
    if not abstract:
        # I keep missing abstracts separate from negative term matches.
        row.update(Status="No abstract", Details="No non-empty primary abstract")
        return row
    text = abstract.casefold()
    row.update(Status="OK", Details="")
    # I check literal text, not related concepts or synonyms.
    row["chemokines"] = "Yes" if "chemokines" in text else "No"
    row["COVID-19"] = "Yes" if "covid-19" in text else "No"
    return row


def run_pipeline(pmids):
    """Process each PMID and keep going if a record fails."""
    rows = []
    for index, pmid in enumerate(pmids):
        if index:
            # I wait after each request finishes: at most 2.5 requests/second.
            time.sleep(0.4)
        try:
            xml_payload = get_pubmed_data(pmid)
            row = inspect_record(pmid, xml_payload)
        except requests.RequestException as exc:
            row = dict(zip(FIELDS, [str(pmid), "Request failed", "N/A", "N/A", str(exc)]))
        except (ET.ParseError, UnicodeError, ValueError) as exc:
            row = dict(zip(FIELDS, [str(pmid), "Parsing failed", "N/A", "N/A", str(exc)]))
        rows.append(row)
    return rows


def print_table(rows):
    """Print the same columns used in the CSV."""
    def cell(value):
        return " ".join(str(value).split()).replace("|", "/")

    print("| " + " | ".join(FIELDS) + " |")
    print("| " + " | ".join("---" for _ in FIELDS) + " |")
    for row in rows:
        print("| " + " | ".join(cell(row[field]) for field in FIELDS) + " |")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pmids", nargs="+", type=int, default=PMID_LIST)
    parser.add_argument("--output", type=Path, default=Path("pubmed-results.csv"))
    args = parser.parse_args()
    results = run_pipeline(args.pmids)
    print_table(results)
    with args.output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    print(f"Saved results to {args.output}")
