"""FastAPI entry point. Run from the Backend folder:  uvicorn main:app --reload"""
import re
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database
import github_service
import stats
from config import CACHE_TTL_MINUTES, FRONTEND_DIR
from github_service import GitHubError
from matcher import band, vibe_check

app = FastAPI(title="GitHub Developer Portfolio")
database.init_db()

USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$")


def check_username(username):
    if not USERNAME_RE.match(username):
        raise HTTPException(400, "That is not a valid GitHub username")


def is_fresh(last_updated):
    age = datetime.now(timezone.utc) - datetime.fromisoformat(last_updated)
    return age < timedelta(minutes=CACHE_TTL_MINUTES)


def get_bundle(username, refresh=False):
    """Cache manager. Returns (data, source) with source = cache | github | stale."""
    cached = database.load_bundle(username)
    if cached and not refresh and is_fresh(cached["user"]["last_updated"]):
        return cached, "cache"
    try:
        user = github_service.fetch_user(username)
        repos = github_service.fetch_repos(username)
        days, heatmap_source = github_service.fetch_contributions(username)
    except GitHubError as exc:
        if cached:  # GitHub failed but we still have old data: serve it
            return cached, "stale"
        raise HTTPException(exc.status, exc.message)
    database.save_bundle(user, repos, days, heatmap_source)
    return database.load_bundle(username), "github"


@app.get("/api/profile/{username}")
def profile(username: str, refresh: bool = False):
    check_username(username)
    bundle, source = get_bundle(username, refresh)
    user, repos = bundle["user"], bundle["repos"]

    own = [r for r in repos if not r["is_fork"]]
    top_repos = sorted(own, key=lambda r: (r["stars"], r["pushed_at"] or ""), reverse=True)[:12]
    saved = database.get_settings(user["username"])
    pct = saved["last_match_pct"] if saved else None

    return {
        "username": user["username"],
        "name": user["name"],
        "bio": user["bio"],
        "avatar_url": user["avatar_url"],
        "followers": user["followers"],
        "following": user["following"],
        "public_repos": user["public_repos"],
        **stats.totals(repos),
        "top_languages": stats.language_distribution(repos),
        "heatmap": stats.build_heatmap(bundle["days"], approximate=user["heatmap_source"] != "graphql"),
        "repos": [{"name": r["name"], "description": r["description"], "language": r["language"],
                   "stars": r["stars"], "forks": r["forks"], "url": r["html_url"], "topics": r["topics"]}
                  for r in top_repos],
        "vibe": {"match_percentage": pct, "band": band(pct)} if pct is not None else None,
        "last_job_description": saved["last_job_description"] if saved else "",
        "cache": {"source": source, "fetched_at": user["last_updated"]},
    }


class VibeRequest(BaseModel):
    username: str
    job_description: str = Field(min_length=20, max_length=20000)


@app.post("/api/vibe")
def vibe(req: VibeRequest):
    check_username(req.username)
    bundle, _ = get_bundle(req.username)
    result = vibe_check(req.job_description, bundle["repos"])
    database.save_match(bundle["user"]["username"], req.job_description, result["match_percentage"])
    return result


# Serve the frontend last so /api/* routes win.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
