# BIS/CBB 634 — Fall 2026 Portfolio

**Name:** Liam Lian  
**NetID:** xl758  
**Course:** Computational Methods for Informatics

## Exercises

- [Studio 1 — Standards exercises](standard-exercises/README.md)
- [Studio 2 — Data structures and analysis of algorithms](dsaa-exercises/README.md)
- [Studio 3 — Big Data](big-data-exercises/README.md)
- [Studio 4 — Internet and APIs](Internet-APIs-exercises/README.md)
- [Studio 5 — Data Exploration 2: PubMed Pipeline, Embeddings, and PCA](data-exploration-exercises/README.md)
- [Studio 6 — Calculus and iterative algorithms](calculus-iterative-exercises/README.md)
- [Studio 7 — Dynamic Programming](dynamic-programming/README.md)

## Organization

Studio 1 exercises share the `standard-exercises/` folder. Their notebooks, README, figures, helper scripts, and required local data live directly in that folder, without additional subfolders. The structure can be revised if the portfolio grows.

Studio 2 exercises share the `dsaa-exercises/` folder and one README. Exercise 1 (1a–1h) covers XML patient data, binary search, and age/gender range queries. Exercise 2 (2a–2c) covers sorting algorithms, runtime benchmarks, log-log analysis, and algorithm selection. Both exercises are complete and documented with notebooks, outputs, and design explanations. The folder also contains figures, saved benchmark results, and a standalone validation script with synthetic test inputs. The course XML input remains local.

Studio 3 covers Bloom filter spelling suggestions, a resumable parallel evaluation of 69 configurations, and a combined performance graph. Its README documents reconstruction leakage, metric definitions, capacity thresholds, expanded edit spaces, and cryptographic versus non-cryptographic hashing. The folder includes the notebook, worker module, final CSV, checkpoint, and figure.

Studio 4 uses the `Internet-APIs-exercises/` folder for PubMed XML retrieval and abstract processing, plus GitHub REST API queries for user metadata and repository star totals. It includes Python scripts, validation code, saved XML/text/CSV/JSON results, and a README describing the API workflow and findings.

Studio 5 uses the `data-exploration-exercises/` folder for exploring the supplied 2023 PubMed embeddings and building a configurable 2025 literature-retrieval, SPECTER embedding, and PCA pipeline. It includes the working notebook, six component-pair plots, an interactive 3D plot, the saved search record, and a README with results, discussion, design choices, and AI assistance. Course input data and generated embedding databases remain local.

Studio 6 uses the `calculus-iterative-exercises/` folder for a custom Explicit Euler SIR simulation and bounded gradient descent against the course simulation API. It includes Python scripts, step-size validation, parameter-sensitivity plots, a cached request ledger, multi-start optimization results, and a README with findings, design choices, and AI assistance.

Studio 7 uses the `dynamic-programming/` folder for forward and reverse DAG sweeps, co-optimal pathway counts, and bottleneck identification in the synthetic EGFR-to-MYC network. It includes the executed notebook, Python scripts, network figures, saved results, validation tests, and a README with analytical answers, design choices, and AI assistance. The original Canvas PDF and input CSV remain local.
