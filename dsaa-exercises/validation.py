"""Standalone synthetic tests for Exercise 1 search functions.

Functions below are copied verbatim from studio-02-xml.ipynb.
Run: python validation.py
Save output: python validation.py > validation-output.txt
No notebook, XML input, or third-party packages are needed.
"""

def binary_search_left(patients, target_age):
    left = 0
    right = len(patients)

    while left < right:
        mid = (left + right) // 2

        if patients[mid]["age"] < target_age:
            left = mid + 1
        else:
            right = mid

    return left


def binary_search_right(patients, target_age):
    left = 0
    right = len(patients)

    while left < right:
        mid = (left + right) // 2

        if patients[mid]["age"] <= target_age:
            left = mid + 1
        else:
            right = mid

    return left


def count_patients_in_range(patients, low_age, high_age):
    if low_age >= high_age:
        return 0

    low_index = binary_search_left(patients, low_age)
    high_index = binary_search_left(patients, high_age)

    return high_index - low_index


def count_patients_by_age_and_gender(
    sorted_patients, male_sorted_patients, low_age, high_age
):
    total_count = count_patients_in_range(
        sorted_patients, low_age, high_age
    )
    male_count = count_patients_in_range(
        male_sorted_patients, low_age, high_age
    )

    return total_count, male_count


# 1e: each input is already sorted by age.
boundary_cases = [
    ("Duplicate target", [40, 41.5, 41.5, 43], 41.5, (1, 3)),
    ("Between existing ages", [40, 42], 41.5, (1, 1)),
    ("Empty input", [], 41.5, (0, 0)),
    ("Above all ages", [40, 42], 50, (2, 2)),
    ("Below all ages", [40, 42], 20, (0, 0)),
]

print("1e - Binary search boundaries")
print("Case | Sorted ages | Target | Expected (left, right) | Actual | Result")
for case, ages, target, expected in boundary_cases:
    patients = [{"age": age} for age in ages]
    actual = (
        binary_search_left(patients, target),
        binary_search_right(patients, target),
    )
    print(f"{case} | {ages} | {target} | {expected} | {actual} | {'PASS' if actual == expected else 'FAIL'}")
    if actual != expected:
        raise AssertionError(case)

# 1f: the left index counts records below the target.
patients = [{"age": age} for age in [40, 41.5, 41.5, 43]]
target_age = 41.5
left_index = binary_search_left(patients, target_age)
count_at_least_target = len(patients) - left_index
print("\n1f - Threshold count")
print(f"Input: [40, 41.5, 41.5, 43]; target: {target_age}; expected: 3; actual: {count_at_least_target}")
if count_at_least_target != 3:
    raise AssertionError("Threshold count")

# 1g: these inputs reproduce every row of the README table.
range_cases = [
    ("Exact endpoints and duplicates", [40, 40, 45, 50, 50], 40, 50, 3),
    ("Between existing ages", [40, 45, 50], 41, 49, 1),
    ("Bounds beyond data", [40, 45, 50], 0, 100, 3),
    ("Entirely below data", [40, 45, 50], 0, 30, 0),
    ("Entirely above data", [40, 45, 50], 60, 70, 0),
    ("Equal bounds", [40, 45, 50], 45, 45, 0),
    ("Reversed bounds", [40, 45, 50], 50, 40, 0),
    ("Empty input", [], 40, 50, 0),
]

print("\n1g - Age range counts")
print("Case | Sorted ages | Query interval | Expected | Actual | Result")
for case, ages, low_age, high_age, expected in range_cases:
    patients = [{"age": age} for age in ages]
    actual = count_patients_in_range(patients, low_age, high_age)
    print(f"{case} | {ages} | [{low_age}, {high_age}) | {expected} | {actual} | {'PASS' if actual == expected else 'FAIL'}")
    if actual != expected:
        raise AssertionError(case)

# 1h: these inputs reproduce the three synthetic README cases.
gender_cases = [
    ("Duplicate endpoints", [(40, "male"), (40, "female"), (45, "unknown"), (50, "male")], 40, 50, (3, 1)),
    ("No male records", [(40, "female"), (45, "unknown")], 40, 50, (2, 0)),
    ("Empty input", [], 40, 50, (0, 0)),
]

print("\n1h - Age and gender counts")
print("Case | Sorted (age, gender) records | Query interval | Expected (total, male) | Actual | Result")
for case, records, low_age, high_age, expected in gender_cases:
    sorted_patients = [{"age": age, "gender": gender} for age, gender in records]
    male_sorted_patients = [
        patient
        for patient in sorted_patients
        if patient["gender"] == "male"
    ]
    actual = count_patients_by_age_and_gender(
        sorted_patients, male_sorted_patients, low_age, high_age
    )
    print(f"{case} | {records} | [{low_age}, {high_age}) | {expected} | {actual} | {'PASS' if actual == expected else 'FAIL'}")
    if actual != expected:
        raise AssertionError(case)

print("\nAll 17 synthetic test cases passed.")
