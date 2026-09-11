"""Download the NYT state-level snapshot used by Studio 1 and verify its hash."""
import hashlib
from pathlib import Path
from urllib.request import urlopen

URL = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv"
EXPECTED_SHA256 = "0b202f6ac8bad66b70b9e344c07155e3f1ce9338f86192af072b56ce448dfc43"
DESTINATION = Path(__file__).resolve().parent / "us-states.csv"


def main():
    if DESTINATION.exists():
        content = DESTINATION.read_bytes()
    else:
        with urlopen(URL, timeout=60) as response:
            content = response.read()
    if hashlib.sha256(content).hexdigest() != EXPECTED_SHA256:
        raise ValueError("Data hash mismatch: existing file preserved; check the source snapshot.")
    if not DESTINATION.exists():
        DESTINATION.parent.mkdir(parents=True, exist_ok=True)
        DESTINATION.write_bytes(content)
    print(f"Verified input: {DESTINATION}")


if __name__ == "__main__":
    main()
