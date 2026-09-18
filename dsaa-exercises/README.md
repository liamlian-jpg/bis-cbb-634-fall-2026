# Studio 2 — Data Structures and Analysis of Algorithms

[Back to course portfolio](../README.md)

**Author:** Liam Lian (xl758)  
**Course:** BIS/CBB 634, Fall 2026

## Code and progress

[Exercise 1 notebook](studio-02-xml.ipynb) contains the code and saved outputs for tasks 1a–1d. Tasks 1e–1h and Exercise 2 are not completed in this update.

To reproduce, download `patients.xml` from the authorized [Canvas data file](https://yale.instructure.com/courses/121398/files/13049637) and place it next to the notebook. The XML input remains local and is excluded from Git. In an environment with NumPy, pandas, matplotlib, and Jupyter installed, run from this folder:

```bash
jupyter notebook studio-02-xml.ipynb
```

Restart the kernel and run the cells in order. The notebook uses a relative input path.

## 1a — Parse XML and analyze age distribution

I parsed the XML with Python's standard-library `xml.etree.ElementTree`. The root is `patientdata`; `generated` and `institution` describe the file, while `patients` contains individual `patient` elements. Each patient stores `age`, `gender`, and `name` as attributes. Attribute order does not affect parsing.

I converted patient records to a pandas DataFrame and converted age text to numeric floating-point values without intentionally rounding them. Diagnoses are child elements and can occur more than once, so I preserved them as lists. Nested `testresults/weight` entries retain their numeric value, date, and units in lists of dictionaries. Empty lists mean that no corresponding entry was recorded, not that a patient has no disease or weighs zero.

### Histogram choice

After discussing different binning choices with classmates, we agreed that a **5-year bin width** provided the clearest view of the age distribution. I used this width for the histogram to balance detail and readability. The comparison was discussed in class; the notebook contains the selected histogram rather than a claim that several alternative plots were generated.

![Patient ages with a 5-year bin width](age_distribution.png)

### Duplicate analysis and binary-search reflection

The dataset contains **324,357 patients**. Counting the parsed, unrounded age values produced:

```text
Any exact duplicate ages: False
Number of distinct ages shared by patients: 0
Total patients with a shared age: 0
```

This is an exact-equality check on the parsed numeric values, not a comparison of rounded ages or histogram groups. Decimal ages can still repeat; many decimal places alone do not establish uniqueness. The printed DataFrame precision only affects display.

No exact duplicate ages were found, so an exact-match binary search would return at most one patient for a given age in this dataset. If duplicate ages were present, stopping at any matching element would retrieve only one patient. To retrieve all matches, I would find the first matching position with a left-boundary search and the position just after the last match with a right-boundary search, then take the slice between them. Boundary searching takes O(log n); retrieving k matching records takes an additional O(k). Binary search is a later task and is not implemented in the current notebook.

## 1b — Gender distribution and encoding

Gender is a string attribute inside the opening `<patient>` tag, alongside age and name. The distinct categories found are:

| Gender | Patient count |
| --- | ---: |
| female | 165,293 |
| male | 158,992 |
| unknown | 72 |

I chose a pie chart to emphasize each category's share of the total. Female and male patients each make up close to half of the dataset. The `unknown` category accounts for approximately 0.02%, so its slice is very small; the legend includes both counts and percentages to keep it visible in the interpretation. I retained `unknown` as the recorded category.

![Patient gender distribution](gender_distribution.png)

## 1c — Age sorting and top-K retrieval

I converted the DataFrame into a list of patient dictionaries using `df.to_dict(orient="records")`, then sorted it in ascending age order using `sorted(..., key=lambda patient: patient["age"])`. The resulting `sorted_patients` list preserves each patient's fields. The final element, `sorted_patients[-1]`, is the oldest patient; the notebook also displays the five oldest records.

The oldest patient is **Monica Caponera**, age **84.99855742449432**, gender **female**. Sorting takes O(n log n) time in the general case; retrieving the final element afterward takes O(1).

## 1d — Single-pass second-oldest retrieval

I proposed scanning the original, unsorted patient list once while maintaining the oldest and second-oldest records. I store them in a two-element list: `top_two[0]` holds the oldest patient and `top_two[1]` holds the second oldest.

For each record, if its age exceeds the current maximum, I first move the previous oldest record into second place and then store the new oldest record. Otherwise, if its age exceeds the current second-oldest age, I replace only the second entry. The `None` initial values allow the first two records to populate the list, and a guard requires at least two patients.

The algorithm uses **O(n) time and O(1) extra space**, beyond the existing patient list: it makes one pass and maintains only two record references. It does not use the sorted list from 1c to compute the result. Equal ages can occupy both positions when they belong to different patient records; this retrieves the second-oldest patient, not the second distinct age.

The second-oldest patient is **Raymond Leigh**, age **84.9982928781625**, gender **male**. Executing all six notebook cells in order reproduced the documented counts, and the single-pass top two matched the two oldest records from the sorted list.

### Conceptual reflection

A single-pass approach is preferable when only the second-oldest patient is needed, because it avoids sorting the entire dataset. Sorting is more useful when repeated rank-based queries are required, such as retrieving the 10th- or 100th-oldest patient, or when every record needs an age rank. After an initial O(n log n) sort, each lookup by a known rank takes O(1) time. In the ascending list, the 10th-oldest patient is `sorted_patients[-10]`. Assigning an explicit rank to all records requires an additional O(n) pass; the current notebook does not add a rank field.

Looking up an individual by name to find their rank is a different operation and would require a separate index for fast queries. If equal ages existed, assigning numeric ranks would also require an explicit tie policy.

## Development and AI assistance

I inspected the XML structure and expanded the initial attribute-only parsing to preserve diagnoses and nested weight records. I selected 5-year age bins after classroom discussion, chose the gender pie chart, and proposed both the single-pass top-two algorithm and the use of a two-element list. I identified repeated ranking queries and explicit per-record ranks as reasons to prefer upfront sorting.

I used OpenAI Codex to help implement these choices, explain binary-search boundaries and complexity, and write this README. I retained responsibility for the substantive decisions and interpretations. The notebook outputs record the work completed so far; later search tasks are not presented as implemented.
