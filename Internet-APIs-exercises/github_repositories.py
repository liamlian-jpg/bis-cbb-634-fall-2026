"""Read a profile, follow repository pages, and add up their stars."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests


def collect_github_data(username, per_page=30):
    """Keep the fetched pages and headers alongside the final totals."""
    username = username.strip()
    if not username or not 1 <= per_page <= 100:
        raise ValueError("Supply a username and a page size from 1 to 100")
    audit = []
    remaining = None
    reset = None
    with requests.Session() as session:
        session.headers.update({"User-Agent": "bis634-studio4",
                                "Accept": "application/vnd.github+json"})

        def fetch(url, params=None):
            nonlocal remaining, reset
            # I stop before another request when the reported budget is empty.
            if remaining == "0":
                raise RuntimeError(f"Rate limit exhausted; retry after Unix time {reset}")
            response = session.get(url, params=params, timeout=30)
            remaining = response.headers.get("X-RateLimit-Remaining")
            reset = response.headers.get("X-RateLimit-Reset")
            audit.append({"url": response.url, "status": response.status_code,
                          "headers": dict(response.headers)})
            response.raise_for_status()
            return response

        base = f"https://api.github.com/users/{quote(username, safe='')}"
        profile = fetch(base).json()
        url = base + "/repos"
        params = {"type": "owner", "per_page": per_page,
                  "sort": "full_name", "direction": "asc"}
        repos = []
        page_counts = []
        seen_urls = set()
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

    ids = [repo["id"] for repo in repos]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate repositories across pages; rerun before reporting a total")
    if any(repo["private"] or repo["owner"]["login"].casefold() != profile["login"].casefold()
           for repo in repos):
        raise ValueError("Unexpected private repository or owner")
    if len(repos) != profile["public_repos"]:
        raise ValueError("Repository count differs from the profile; check for changes and rerun")
    # I include owned forks: the question asks for all owned public repositories.
    return {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "profile": profile, "repositories": repos,
            "page_counts": page_counts, "request_audit": audit,
            "total_stars": sum(repo["stargazers_count"] for repo in repos)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("--per-page", type=int, default=30)
    parser.add_argument("--output", type=Path, default=Path("github-results.json"))
    args = parser.parse_args()
    result = collect_github_data(args.username, args.per_page)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    profile = result["profile"]
    print("| Username | Public repositories | Account created (UTC) | Total stars |")
    print("| --- | --- | --- | --- |")
    print(f"| {profile['login']} | {profile['public_repos']} | {profile['created_at']} | {result['total_stars']} |")
    print(f"Repository page sizes: {result['page_counts']}")
    print(f"Unique repositories checked: {len(result['repositories'])}")
    print("Count matches profile: Yes")
    print("Next page remaining: No")
    print("\n| Request | X-RateLimit-Limit | X-RateLimit-Remaining |")
    print("| --- | --- | --- |")
    for i, entry in enumerate(result['request_audit'], 1):
        headers = requests.structures.CaseInsensitiveDict(entry['headers'])
        print(f"| {i} | {headers.get('X-RateLimit-Limit', 'N/A')} | {headers.get('X-RateLimit-Remaining', 'N/A')} |")
    print(f"Saved results to {args.output}")
