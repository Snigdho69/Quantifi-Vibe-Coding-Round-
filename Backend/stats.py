"""Every dashboard calculation lives here (server side). Pure functions, no I/O."""
import math
from collections import Counter
from datetime import date, timedelta


def totals(repos):
    return {
        "total_stars": sum(r["stars"] or 0 for r in repos),
        "total_forks": sum(r["forks"] or 0 for r in repos),
    }


def language_distribution(repos, top=6):
    """Share of the user's own (non-fork) repos by primary language, for the pie chart."""
    counts = Counter(r["language"] for r in repos if r["language"] and not r["is_fork"])
    total = sum(counts.values())
    if not total:
        return []
    items = counts.most_common(top)
    rest = total - sum(c for _, c in items)
    if rest:
        items.append(("Other", rest))
    return [{"language": lang, "count": c, "percent": round(c * 100 / total, 1)} for lang, c in items]


def level_for(count, peak):
    """Heatmap intensity 0-4, relative to the user's busiest day."""
    if count <= 0 or peak <= 0:
        return 0
    return min(4, math.ceil(count * 4 / peak))


def streaks(by_day, start, end):
    """(current, longest) run of consecutive days with at least one contribution."""
    longest = run = 0
    d = start
    while d <= end:
        run = run + 1 if by_day.get(d, 0) > 0 else 0
        longest = max(longest, run)
        d += timedelta(days=1)
    # Today may not have activity yet, so the current streak can end yesterday.
    d = end if by_day.get(end, 0) > 0 else end - timedelta(days=1)
    current = 0
    while d >= start and by_day.get(d, 0) > 0:
        current += 1
        d -= timedelta(days=1)
    return current, longest


def build_heatmap(days, approximate=False):
    """Last 365 days as Sunday-to-Saturday weeks of {date, count, level} (None = padding)."""
    by_day = {date.fromisoformat(d): n for d, n in days}
    end = max([date.today(), *by_day])
    start = end - timedelta(days=364)
    span = [start + timedelta(days=i) for i in range(365)]
    peak = max(by_day.get(d, 0) for d in span)

    cells = [{"date": d.isoformat(), "count": by_day.get(d, 0), "level": level_for(by_day.get(d, 0), peak)}
             for d in span]
    cells = [None] * ((start.weekday() + 1) % 7) + cells  # align first day to its weekday row
    cells += [None] * (-len(cells) % 7)
    current, longest = streaks(by_day, start, end)
    return {
        "weeks": [cells[i:i + 7] for i in range(0, len(cells), 7)],
        "total": sum(by_day.get(d, 0) for d in span),
        "current_streak": current,
        "longest_streak": longest,
        "approximate": approximate,
    }
