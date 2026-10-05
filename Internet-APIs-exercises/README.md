# Studio 4 — Internet and APIs

[Back to course portfolio](../README.md)

**Course:** BIS/CBB 634 — Computational Methods for Informatics, Fall 2026  
**Author:** Liam Lian (xl758)

This folder contains a PubMed XML retrieval and abstract-processing pipeline,
and GitHub REST API queries for user metadata and repository star totals.

Run the commands below from this folder with Python 3 and `requests` installed.
Saved XML, text, CSV, and JSON files contain the October 4, 2026 results.

## Exercise 1 — PubMed

### Programmatic Efetch Querying & Schema Analysis

[`pubmed.py`](pubmed.py) implements `get_pubmed_data(pmid)` using `requests`.
It sends `db=pubmed`, the supplied `id`, and `retmode=xml` to NCBI EFetch,
then returns the UTF-8 XML string. Request parameters are passed through
`params` rather than assembled by string concatenation. A 30-second timeout
prevents indefinite waiting, and `raise_for_status()` exposes HTTP failures.
Invalid identifier inputs are rejected before requesting data. The function
does not assume that HTTP success implies a valid article or an abstract.

Run from this directory with Python and `requests` installed:

```bash
python pubmed.py 34807729 --output pubmed-34807729.xml
```

Key retrieval function from `pubmed.py` (`requests` and `EFETCH_URL` are
defined in that module):

```python
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
```

#### Metadata Assessment: PMID 34807729

The live EFetch response was saved on October 4, 2026 as
[`pubmed-34807729.xml`](pubmed-34807729.xml). It contains 8,518 Unicode
characters. XML parsing succeeded and the returned citation PMID matched
34807729. The root is `PubmedArticleSet`, containing one `PubmedArticle`.
The article has two main branches: `MedlineCitation` and `PubmedData`.

| Category | XML location and observed contents |
| --- | --- |
| Identifiers | `MedlineCitation/PMID` and `PubmedData/ArticleIdList` contain PMID 34807729. DOI `10.1089/omi.2021.0155` occurs in the article's `ELocationID` and in `ArticleIdList`. |
| Bibliographic metadata | `Article` contains the article title, journal, volume 25, issue 12, pages 770–781, language `eng`, publication types, and electronic publication date 2021-11-22. `Journal/Title` is *Omics : a journal of integrative biology*; `ArticleTitle` identifies the individual paper. |
| Authors and affiliations | `Article/AuthorList` contains four authors with names and affiliations; one author has an ORCID identifier. |
| Abstract structure | `Article/Abstract` contains exactly one `AbstractText`, with no `Label` or `NlmCategory` attributes and no nested child elements. This is an unstructured single-block abstract, not labeled OBJECTIVE/METHODS/RESULTS sections. |
| Controlled vocabulary | `MeshHeadingList` contains 11 headings, including COVID-19, Cytokine Release Syndrome, and Models, Theoretical. Descriptors and qualifiers include vocabulary IDs and major-topic flags. `ChemicalList` contains Cytokines and Nitric Oxide with substance identifiers. |
| Keywords | `KeywordList` contains six keywords, including biochemical systems theory and biomarkers. This list is separate from MeSH indexing. |
| Funding information | No `GrantList` or `Grant` elements are present. A publication type says `Research Support, Non-U.S. Gov't`, but this is a classification, not a named funder or grant number. Missing grant metadata does not establish that the study had no funding. |
| Record history | `DateCompleted`, `DateRevised`, and `PubmedData/History` describe record processing/indexing dates. These are distinct from journal and electronic publication dates. |

### Dynamic Parsing & Logic Construction

`extract_abstract(xml_payload)` in `pubmed.py` returns the primary abstract as
plain text. It visits every `AbstractText` in document order, collects text
with `"".join(section.itertext())`, prefixes any `Label`, and separates sections
with blank lines. Unlike `.text`, `itertext()` preserves nested inline text
and text following child elements. It does not insert spaces within words
split by inline tags. XML entities are decoded by the XML parser.

The maintained extraction function uses `xml.etree.ElementTree as ET`:

```python
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
```

Both records were fetched and their extracted abstracts printed and saved:

| PMID | Observed structure | Saved output |
| --- | --- | --- |
| 34807729 | One `AbstractText`, no labels or child tags | [Complete abstract](abstract-34807729.txt) |
| 32299786 | Five `AbstractText` elements labeled BACKGROUND, AIM, METHOD, RESULTS, CONCLUSION; each also has `NlmCategory`; no child tags within these elements | [Complete abstract](abstract-32299786.txt) |

The [second raw XML](pubmed-32299786.xml) was fetched October 4, 2026.
The parser uses the source `Label` (for example AIM), rather than substituting
the normalized `NlmCategory` (OBJECTIVE). The single-block record needs no
special-case code: the same loop simply runs once. The structured record
requires all five blocks; selecting only the first would lose four sections.
The source spelling and punctuation are preserved, including `treatment.When`
in the second record.

Completeness was checked using an independent `xml.dom.minidom` traversal of
the saved XML: every abstract text node, section label, and section order was
compared exactly with the function output. Both PMID identities were also
checked. This verifies completeness relative to these XML snapshots, not the
publisher's full text. Neither real example has inline child tags, so an
explicit synthetic fixture tests nested italics, subscript, trailing text,
and an escaped ampersand. Additional fixtures cover missing/empty abstracts,
malformed XML, and rejection of multiple records.

```bash
python validate_abstract.py
```

To print the two saved-record abstracts without making new requests:

```python
from pathlib import Path
from pubmed import extract_abstract

for pmid in (34807729, 32299786):
    payload = Path(f"pubmed-{pmid}.xml").read_text(encoding="utf-8")
    print(pmid)
    print(extract_abstract(payload))
```

All of these checks passed. A missing abstract returns an empty string;
malformed XML raises `ParseError` for the later pipeline to catch. More than
one record raises `ValueError` to avoid silently combining different papers.
Extraction targets the primary article/book abstract, not translated
`OtherAbstract` content or unrelated text elsewhere in the record.

### Pipeline Execution & Term Identification

Retrieval is separate from abstract extraction so that networking and XML
interpretation can be checked independently. Retrieval, abstract extraction, and the
two-record differential check are implemented and executed.

[`pubmed_pipeline.py`](pubmed_pipeline.py) accepts the nine assigned PMIDs by
default, waits 0.4 seconds between completed requests, and prints an English
table with `PMID`, `Status`, `chemokines`, `COVID-19`, and `Details` columns.
It also writes the same fields to `pubmed-results.csv` when run. Term checks
use case-insensitive literal substring matching. Missing data and failures
use `N/A`, not `No`.

```bash
python pubmed_pipeline.py
```

Offline checks passed on the two saved records and simulated request failure,
malformed XML, empty record set, missing abstract, and mismatched PMID cases.
The simulated batch continued after failures and called the wait between
records. The nine-record network run completed on October 4, 2026 and saved
[pubmed-results.csv](pubmed-results.csv). Eight records had a non-empty primary
abstract. PMID 41916485 returned a matching record but no non-empty primary
abstract, so both term fields are `N/A`. The remaining records were processed
successfully. The full results are shown below.

| PMID | Status | chemokines | COVID-19 | Details |
| --- | --- | --- | --- | --- |
| 34807729 | OK | Yes | Yes | |
| 21943025 | OK | No | No | |
| 33980688 | OK | Yes | Yes | |
| 32299786 | OK | Yes | No | |
| 20725509 | OK | No | No | |
| 41916485 | No abstract | N/A | N/A | No non-empty primary abstract |
| 17245822 | OK | No | No | |
| 31842501 | OK | No | No | |
| 35064122 | OK | No | Yes | |

### Data Quality & Edge-Case Audit

I inspected the [XML for PMID 41916485](pubmed-41916485.xml), also available
as a [readable copy](pubmed-41916485-readable.xml). The record includes the
article title, authors, affiliations, journal information, and dates, but no
`Abstract` or `AbstractText` element. This is missing abstract data in the
returned PubMed record, not a different abstract structure missed by the
parser. It does not establish whether the publisher provides an abstract.

An expression such as `article.find("Abstract/AbstractText").text` would
raise `AttributeError` here because `find()` returns `None`. My parser uses
`findall()` and iterates over the matching elements. With no matches, it
returns an empty string. The pipeline then records `No abstract` and `N/A`
for both terms and continues to the next PMID. I use `N/A` because there is
no abstract to check; `No` would incorrectly imply a completed negative check.
The live run processed the three following records successfully.

Request failures and malformed XML are handled separately by the batch loop,
with an explanatory status instead of stopping the whole run. Those failure
paths were tested offline; they were not observed in this nine-record live run.

Verification inspected the saved XML, confirmed record identity and hierarchy,
and counted the elements summarized above. The saved response is a snapshot;
future PubMed metadata may change.

### References

- [NCBI EFetch parameters](https://www.ncbi.nlm.nih.gov/sites/books/NBK25499/)
- Assignment: *Internet and APIs*, Exercise 1, pages 1–3.

### Exercise 1 — Code evolution and design choices

I worked through this exercise in stages: retrieving a record by PMID,
extracting its abstract, and then reviewing the batch output. Using `requests`
and the supplied PMIDs was required by the assignment. Codex introduced the
separate retrieval and parsing functions and explained why `itertext()` keeps
text inside nested tags. This separation makes the parser reusable on saved
XML without another network request.

I inspected the XML for PMID 41916485 after the batch reported `No abstract`.
I could see the title, authors, affiliations, journal, and dates, but no
abstract. That review distinguished missing data from a parser that might
have missed a different structure. I also clarified that these are PubMed
records, not full-text articles. Returning `N/A` preserves that distinction
in the keyword results. The 0.4-second delay is a simple conservative choice
for this small sequential run; it does not coordinate other processes sharing
an IP address.

### Exercise 1 — AI assistance

I used OpenAI Codex to generate the Python functions and batch script, explain
the XML structure, run the API requests and tests, and draft the documentation.
I reviewed the input/output workflow and personally inspected the missing-
abstract record. Codex performed the execution and automated checks. The code was developed with assistance, and I
remain responsible for understanding and explaining the submitted work.

## Exercise 2 — RESTful API

### Part 1: API Query Architecture

`GET /users/{username}` returns user metadata in JSON, the default data
interchange format. `public_repos` gives the public repository count and
`created_at` gives account creation time. The user payload has no total-stars
field; that answer requires the repository list and aggregation. Pagination
and completeness checks are described with the implementation below.

### Implementation & Script Construction

#### 1. User Profile Extraction

I pass the username as a command-line argument to
[`github_profile.py`](github_profile.py). The script requests
`GET /users/{username}` with a custom `User-Agent`, reads the JSON response,
and prints `public_repos` and `created_at`.

```bash
python github_profile.py ramcdougal
```

The live request on October 4, 2026 returned:

| Username | Public repositories | Account created (UTC) |
| --- | --- | --- |
| ramcdougal | 45 | 2014-02-13T03:10:45Z |

The profile and HTTP response headers were saved in
[`github-profile.json`](github-profile.json) for inspection and the later
rate-limit audit. These counts describe this response and may change.
#### 2. Repository Stargazer Aggregation

The user endpoint returns `public_repos` and `created_at` directly in JSON,
but it does not provide a total star count across repositories. I request
`GET /users/{username}/repos` and add each repository's `stargazers_count`.
This measures stars received by owned repositories, not repositories starred
by the user. Owned public forks are included.

[`github_repositories.py`](github_repositories.py) runs the complete workflow:

```bash
python github_repositories.py ramcdougal
```

I use `per_page=30` so this account exercises pagination in the live run.
After each page, I follow the `rel="next"` URL from the HTTP `Link` header,
which supplies the next page's parameters. The loop stops only when there
is no next link. Increasing `per_page` can reduce requests, but setting a
larger page size alone does not guarantee all repositories were retrieved.

The pagination loop below is an excerpt from `collect_github_data`; `fetch`,
`url`, `params`, and the result lists are initialized earlier in that function.

```python
while url:
    if url in seen_urls:
        raise RuntimeError("Repeated next-page URL")
    seen_urls.add(url)
    response = fetch(url, params)
    page = response.json()
    if not isinstance(page, list):
        raise ValueError("Expected a repository list")
    repos.extend(page)
    page_counts.append(len(page))
    # I follow GitHub's next link rather than guessing the last page.
    url = response.links.get("next", {}).get("url")
    params = None
```

After validation, the total is calculated with
`sum(repo["stargazers_count"] for repo in repos)`.

The October 4, 2026 run returned:

| Username | Public repositories | Account created (UTC) | Total stars |
| --- | ---: | --- | ---: |
| ramcdougal | 45 | 2014-02-13T03:10:45Z | 29 |

The repository pages contained 30 and 15 records. All 45 repository IDs were
unique, all owners matched the requested account, all records were public,
and the count matched `public_repos`. The final response had no next-page
link. The full repository data and request headers are saved in
[`github-results.json`](github-results.json), and the star sum was checked again
from that saved data. These checks support completeness for this run;
separate API requests are not an atomic snapshot if repositories change
during pagination. A count mismatch or duplicate causes the script to stop
rather than report a potentially incomplete total.

### Data Quality, Rate Limits & Edge-Case Audit

GitHub's default unauthenticated primary limit is 60 requests per hour per
originating IP address. The run made one profile request and two repository
requests, with these observed response headers:

| Request | X-RateLimit-Limit | X-RateLimit-Remaining |
| --- | ---: | ---: |
| Profile | 60 | 58 |
| Repository page 1 | 60 | 57 |
| Repository page 2 | 60 | 56 |

I check the remaining budget before the next request. If it is zero, this
script stops with the reset timestamp rather than immediately retrying.
An offline simulated response verified that no second request was made
after a zero-budget response. The live run did not exhaust the limit.

In production, I would save progress and defer the next request until after
`X-RateLimit-Reset` (a Unix timestamp). If `Retry-After` is present, I would
also honor that delay. A secondary-limit response can occur even with a
nonzero primary budget; I would reduce request frequency and use bounded
backoff instead of repeated immediate retries. The current script propagates
HTTP errors and does not implement automatic waiting, retries, or resumption.

### Sources and verification

- [GitHub user endpoints](https://docs.github.com/en/rest/users/users)
- [GitHub repository endpoints](https://docs.github.com/en/rest/repos/repos)
- [Pagination](https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api)
- [Rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
- [API best practices](https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api)

### Exercise 2 — Code evolution and design choices

I first reviewed the profile-query output, then continued to the repository
query. I implemented the combined script with a username argument and a
custom `User-Agent`, as the assignment requires. The user endpoint supplies
two answers directly, while the star total needs a sum over repositories.

I selected a page size of 30, making the 45-repository example span two
pages. This uses one more repository request than a page size of 100 but
provides a live check of the next-link logic. The script checks unique IDs,
owner, visibility, and the profile count before reporting the total. These
checks help catch omissions or changing data without claiming an atomic
snapshot. The current script stops on exhausted quota; automatic resumption
is discussed as a production extension, not an implemented feature.

### Exercise 2 — AI assistance

I used OpenAI Codex to implement and execute the profile and repository
queries, inspect response headers, verify the saved totals, and write the
README. Codex explained pagination and rate limits and supplied the
implementation choices described above. The outputs were presented to me
in the discussion. I remain responsible for understanding the implementation and
its limitations.
