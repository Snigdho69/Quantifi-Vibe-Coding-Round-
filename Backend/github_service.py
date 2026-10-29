"""GitHub access: REST for profile + repos, GraphQL for the 365-day contribution calendar."""
from collections import Counter

import requests

from config import GITHUB_TOKEN

API = "https://api.github.com"
TIMEOUT = 15

CALENDAR_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionCalendar { weeks { contributionDays { date contributionCount } } } }
  }
}"""


class GitHubError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


def _headers():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "portfolio-dashboard"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def _get(path, **params):
    try:
        r = requests.get(f"{API}{path}", headers=_headers(), params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise GitHubError(502, f"Could not reach GitHub: {exc}")
    if r.status_code == 404:
        raise GitHubError(404, "GitHub user not found")
    if r.status_code == 401:
        raise GitHubError(401, "GITHUB_TOKEN is invalid or expired")
    if r.status_code in (403, 429):
        raise GitHubError(429, "GitHub rate limit reached. Add a GITHUB_TOKEN or try again later")
    if not r.ok:
        raise GitHubError(502, f"GitHub returned an error ({r.status_code})")
    return r.json()


def fetch_user(username):
    return _get(f"/users/{username}")


def fetch_repos(username):
    repos = []
    for page in range(1, 6):  # up to 500 repos
        batch = _get(f"/users/{username}/repos", per_page=100, page=page, type="owner", sort="pushed")
        repos += batch
        if len(batch) < 100:
            break
    return repos


def _calendar_days(username):
    r = requests.post(f"{API}/graphql", headers=_headers(), timeout=TIMEOUT,
                      json={"query": CALENDAR_QUERY, "variables": {"login": username}})
    r.raise_for_status()
    weeks = r.json()["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def _event_days(username):
    """Fallback without a token: count public events per day (GitHub only keeps ~90 days)."""
    counts = Counter()
    for page in (1, 2, 3):
        events = _get(f"/users/{username}/events/public", per_page=100, page=page)
        if not events:
            break
        for e in events:
            counts[e["created_at"][:10]] += 1
    return sorted(counts.items())


def fetch_contributions(username):
    """Return ([(date, count), ...], source) where source is 'graphql' or 'events'."""
    if GITHUB_TOKEN:
        try:
            return _calendar_days(username), "graphql"
        except (requests.RequestException, KeyError, TypeError):
            pass  # fall through to the approximate version
    return _event_days(username), "events"
