"""Reproduce Exercise 1 checks using the code in the trusted local notebook.

Run: python validation.py --output validation-output.txt
Requires the notebook dependencies and the Canvas patients.xml input.
"""
import argparse
import ast
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

BASE = Path(__file__).resolve().parent


def validate(notebook_path, data_path):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "studio2-validation-mpl"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd

    print("Exercise 1 validation")
    print("Python:", sys.version.split()[0])
    print("NumPy:", np.__version__, "pandas:", pd.__version__, "matplotlib:", matplotlib.__version__)
    for label, path in [("Notebook", notebook_path), ("XML", data_path)]:
        print(f"{label} SHA-256: {hashlib.sha256(path.read_bytes()).hexdigest()}")
    notebook = json.loads(notebook_path.read_text())
    scope = {"display": lambda *args, **kwargs: None, "__name__": "__validation__"}
    # Execute original notebook algorithms. Override only its machine-specific input path.
    # Display calls are suppressed; plotting code still runs with a noninteractive backend.
    original_show = plt.show
    plt.show = lambda *args, **kwargs: None
    cell_count = 0
    path_overrides = 0
    print("\nNotebook execution (record-level output suppressed):")
    try:
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            tree = ast.parse("".join(cell["source"]))
            for statement in tree.body:
                if isinstance(statement, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "file_path"
                    for target in statement.targets
                ):
                    statement.value = ast.Constant(str(data_path))
                    path_overrides += 1
            ast.fix_missing_locations(tree)
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(tree, f"{notebook_path.name}:cell-{index + 1}", "exec"), scope)
            cell_count += 1
    finally:
        plt.show = original_show
        plt.close("all")
    if path_overrides != 1:
        raise AssertionError(f"Expected one file_path assignment, found {path_overrides}")
    print(f"Executed {cell_count} code cells in order.")

    checks = 0

    def check(label, actual, expected):
        nonlocal checks
        if actual != expected:
            raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")
        checks += 1
        print(f"PASS | {label} | actual={actual!r} | expected={expected!r}")

    print("\nData and notebook results:")
    patients = scope["sorted_patients"]
    males = scope["male_sorted_patients"]
    check("1a patient count", len(scope["df"]), 324357)
    check("1a missing ages", int(scope["df"]["age"].isna().sum()), 0)
    check("1a repeated age values", len(scope["duplicate_ages"]), 0)
    check("1b gender counts", scope["gender_counts"].to_dict(), {"female": 165293, "male": 158992, "unknown": 72})
    check("1c ages sorted ascending", all(a["age"] <= b["age"] for a, b in zip(patients, patients[1:])), True)
    check("1c oldest equals full-scan maximum", patients[-1] == max(scope["patients"], key=lambda p: p["age"]), True)
    check("1d linear top two equal sorted top two", scope["top_two"] == list(reversed(patients[-2:])), True)
    check("1e exact match count and target", len(scope["matching_patients"]) == 1 and all(p["age"] == 41.5 for p in scope["matching_patients"]), True)
    check("1e boundaries", (scope["left_index"], scope["right_index"]), (173886, 173887))
    check("1f threshold count", scope["count_at_least_target"], 150471)
    check("1f full-scan comparison", scope["count_at_least_target"], sum(p["age"] >= 41.5 for p in patients))
    check("1g example count", scope["count_patients_in_range"](patients, 40, 50), 42525)
    check("1h male index size", len(males), 158992)
    check("1h example counts", (scope["total_count"], scope["male_count"]), (42525, 20873))

    print("\n1e boundary checks:")
    for ages, target, expected in [([40, 41.5, 41.5, 43], 41.5, (1, 3)), ([40, 42], 41.5, (1, 1)), ([], 41.5, (0, 0)), ([40, 42], 50, (2, 2)), ([40, 42], 20, (0, 0))]:
        records = [{"age": age} for age in ages]
        actual = (scope["binary_search_left"](records, target), scope["binary_search_right"](records, target))
        check(f"ages={ages}, target={target}", actual, expected)

    print("\n1g range checks:")
    for ages, low, high, expected in [([40, 40, 45, 50, 50], 40, 50, 3), ([40, 45, 50], 41, 49, 1), ([40, 45, 50], 0, 100, 3), ([40, 45, 50], 0, 30, 0), ([40, 45, 50], 60, 70, 0), ([40, 45, 50], 45, 45, 0), ([40, 45, 50], 50, 40, 0), ([], 40, 50, 0)]:
        actual = scope["count_patients_in_range"]([{"age": age} for age in ages], low, high)
        check(f"ages={ages}, interval=[{low}, {high})", actual, expected)

    print("\n1h full-data comparisons with independent scans:")
    query = scope["count_patients_by_age_and_gender"]
    for low, high in [(40, 50), (41.5, 50), (0, 100), (-10, 0), (100, 110), (50, 50), (50, 40)]:
        expected = (sum(low <= p["age"] < high for p in patients), sum(low <= p["age"] < high and p["gender"] == "male" for p in patients))
        check(f"interval=[{low}, {high})", query(patients, males, low, high), expected)

    print("\n1h synthetic checks:")
    for label, items, expected in [("Duplicate endpoints", [(40, "male"), (40, "female"), (45, "unknown"), (50, "male")], (3, 1)), ("No male records", [(40, "female"), (45, "unknown")], (2, 0)), ("Empty input", [], (0, 0))]:
        records = [{"age": age, "gender": gender} for age, gender in items]
        male_records = [p for p in records if p["gender"] == "male"]
        check(label, query(records, male_records, 40, 50), expected)
    print(f"\nPASS: {checks} checks; {cell_count} notebook code cells executed.")
    print("Timing complexity is justified in README; these checks verify results, not asymptotic runtime.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=BASE / "patients.xml")
    parser.add_argument("--output", type=Path, help="Save the actual run transcript to this file")
    args = parser.parse_args()
    transcript = io.StringIO()
    status = 0
    with contextlib.redirect_stdout(transcript), contextlib.redirect_stderr(transcript):
        try:
            validate(BASE / "studio-02-xml.ipynb", args.data.resolve())
        except Exception:
            traceback.print_exc()
            print("FAIL: validation did not complete.")
            status = 1
    result = transcript.getvalue()
    print(result, end="")
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
