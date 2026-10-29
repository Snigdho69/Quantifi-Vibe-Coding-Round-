# GitHub Developer Portfolio

Dashboard with a contribution heatmap, repo cards, top-languages pie chart and a job-description "vibe check".
FastAPI + SQLite backend (all calculations server-side); plain HTML/CSS/JS frontend.

## Run
```
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add GITHUB_TOKEN for the full 365-day heatmap
cd Backend && uvicorn main:app --reload
```
Open http://127.0.0.1:8000

## How it works
- `GET /api/profile/{username}`: cache-first (SQLite, 30 min TTL, `?refresh=true` to force). Falls back to the stale cache if GitHub fails.
- `POST /api/vibe`: scores a job description against languages/topics of the cached repos.
- Heatmap uses the GitHub GraphQL contribution calendar (needs `GITHUB_TOKEN`), else public events (approximate).
