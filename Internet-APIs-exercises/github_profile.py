"""Fetch a public GitHub profile for a supplied username."""

import argparse
import json
from pathlib import Path
from urllib.parse import quote

import requests


def get_github_profile(username):
    """Return the profile and response headers for later rate-limit checks."""
    username = username.strip()
    if not username:
        raise ValueError("Username cannot be empty")
    response = requests.get(
        f"https://api.github.com/users/{quote(username, safe='')}",
        headers={
            "User-Agent": "bis634-studio4",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json(), dict(response.headers)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("--output", type=Path, default=Path("github-profile.json"))
    args = parser.parse_args()
    profile, headers = get_github_profile(args.username)
    # I check the fields before saving or reporting a successful result.
    public_repos = profile["public_repos"]
    created_at = profile["created_at"]
    print("| Username | Public repositories | Account created (UTC) |")
    print("| --- | --- | --- |")
    print(f"| {profile['login']} | {public_repos} | {created_at} |")
    # I keep the response headers for the later rate-limit audit.
    args.output.write_text(
        json.dumps({"profile": profile, "response_headers": headers}, indent=2)
        + "\n", encoding="utf-8",
    )
    print(f"Saved profile and response headers to {args.output}")
