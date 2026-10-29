"""Settings, read from the .env file in the project root (never commit .env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "30"))
FRONTEND_DIR = ROOT / "Frontend"
