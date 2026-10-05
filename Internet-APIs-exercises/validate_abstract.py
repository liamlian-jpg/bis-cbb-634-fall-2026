"""Offline validation against saved records and explicit edge-case fixtures."""

from pathlib import Path
from xml.dom import minidom, Node
import xml.etree.ElementTree as ET

from pubmed import extract_abstract


def dom_text(node):
    """Independent DOM traversal for comparison with ElementTree extraction."""
    if node.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE):
        return node.data
    return "".join(dom_text(child) for child in node.childNodes)


def wrap(sections):
    return ("<PubmedArticleSet><PubmedArticle><MedlineCitation><Article>"
            + sections +
            "</Article></MedlineCitation></PubmedArticle></PubmedArticleSet>")


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent
    for pmid, labels in [(34807729, [""]),
                         (32299786, ["BACKGROUND", "AIM", "METHOD", "RESULTS", "CONCLUSION"])]:
        payload = (folder / f"pubmed-{pmid}.xml").read_text(encoding="utf-8")
        dom = minidom.parseString(payload)
        assert dom_text(dom.getElementsByTagName("PMID")[0]) == str(pmid)
        blocks = dom.getElementsByTagName("AbstractText")
        assert [block.getAttribute("Label") for block in blocks] == labels
        expected = []
        for block, label in zip(blocks, labels):
            body = dom_text(block).strip()
            expected.append(f"{label}: {body}" if label else body)
        result = extract_abstract(payload)
        assert result == "\n\n".join(expected)
        assert (folder / f"abstract-{pmid}.txt").read_text(encoding="utf-8") == result + "\n"
        print(f"PASS {pmid}: {len(blocks)} sections; exact text and label agreement")

    assert extract_abstract(wrap('<Abstract><AbstractText Label="RESULTS">'
        'A <i>nested</i> word &amp; H<sub>2</sub>O.'
        '</AbstractText></Abstract>')) == 'RESULTS: A nested word & H2O.'
    assert extract_abstract(wrap('')) == ''
    assert extract_abstract(wrap('<Abstract><AbstractText /></Abstract>')) == ''
    try:
        extract_abstract('<broken>')
    except ET.ParseError:
        pass
    else:
        raise AssertionError('Malformed XML must raise ParseError')
    try:
        extract_abstract('<PubmedArticleSet><PubmedArticle/><PubmedArticle/></PubmedArticleSet>')
    except ValueError:
        pass
    else:
        raise AssertionError('Multiple records must not be silently merged')
    print('PASS fixtures: nested text/tails/entities, missing/empty abstract, malformed XML, multiple records')
