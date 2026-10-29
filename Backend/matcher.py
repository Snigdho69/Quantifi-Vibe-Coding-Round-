"""Vibe check: compare a job description against the languages/topics of the cached repos."""
import re

# (label, regex, GitHub language it implies or None, case_sensitive)
TERMS = [
    ("Python", r"\bpython\b", "Python", False),
    ("JavaScript", r"\b(?:javascript|node\.?js)\b", "JavaScript", False),
    ("TypeScript", r"\btypescript\b", "TypeScript", False),
    ("Java", r"\bjava\b", "Java", False),
    ("C++", r"c\+\+", "C++", False),
    ("C#", r"c#", "C#", False),
    ("C", r"(?<![\w+#.])C(?![\w+#&\-])", "C", True),
    ("Go", r"(?i:\bgolang\b)|\bGo\b", "Go", True),
    ("Rust", r"\brust\b", "Rust", False),
    ("Ruby", r"\bruby\b", "Ruby", False),
    ("PHP", r"\bphp\b", "PHP", False),
    ("Swift", r"\bswift\b", "Swift", False),
    ("Kotlin", r"\bkotlin\b", "Kotlin", False),
    ("Scala", r"\bscala\b", "Scala", False),
    ("Dart", r"\bdart\b", "Dart", False),
    ("R", r"(?<![\w+#.])R(?![\w+#&\-])", "R", True),
    ("HTML", r"\bhtml5?\b", "HTML", False),
    ("CSS", r"\bcss3?\b", "CSS", False),
    ("Shell", r"\b(?:bash|shell script(?:ing)?)\b", "Shell", False),
    ("React", r"\breact(?:\.?js)?\b", "JavaScript", False),
    ("Vue", r"\bvue(?:\.?js)?\b", "JavaScript", False),
    ("Angular", r"\bangular\b", "TypeScript", False),
    ("Django", r"\bdjango\b", "Python", False),
    ("Flask", r"\bflask\b", "Python", False),
    ("FastAPI", r"\bfastapi\b", "Python", False),
    ("PyTorch", r"\bpytorch\b", "Python", False),
    ("TensorFlow", r"\btensorflow\b", "Python", False),
    ("Spring", r"\bspring boot\b|\bspring framework\b", "Java", False),
    ("Docker", r"\bdocker\b", "Dockerfile", False),
    ("SQL", r"\b(?:sql|mysql|postgres(?:ql)?|sqlite)\b", None, False),
    ("Kubernetes", r"\bkubernetes\b|\bk8s\b", None, False),
    ("AWS", r"\baws\b", None, False),
    ("Git", r"\bgit\b", None, False),
    ("Machine learning", r"\bmachine learning\b", None, False),
]


def band(pct):
    return "high" if pct >= 70 else "medium" if pct >= 40 else "low"


def _evidence(repos):
    """Languages used, plus a text blob of repo names/topics/descriptions."""
    langs = {r["language"].lower() for r in repos if r["language"]}
    text = " ".join(f'{r["name"]} {r["description"] or ""} {" ".join(r["topics"])}' for r in repos).lower()
    return langs, text


def vibe_check(job_description, repos):
    found = []
    for label, pattern, lang, case_sensitive in TERMS:
        hits = len(re.findall(pattern, job_description, 0 if case_sensitive else re.I))
        if hits:
            found.append((label, lang, min(hits, 3)))  # cap so one repeated word can't dominate

    if not found:
        return {"match_percentage": 0, "band": "low", "matched": [], "missing": [], "keywords_found": 0,
                "message": "No recognisable tech keywords found in this job description."}

    langs, text = _evidence(repos)
    matched, missing, got, total = [], [], 0, 0
    for label, lang, weight in found:
        total += weight
        in_langs = lang is not None and lang.lower() in langs
        in_text = len(label) > 2 and re.search(rf"(?<![\w+#]){re.escape(label.lower())}(?![\w+#])", text)
        if in_langs or in_text:
            matched.append(label)
            got += weight
        else:
            missing.append(label)

    pct = round(got * 100 / total)
    return {"match_percentage": pct, "band": band(pct), "matched": matched, "missing": missing,
            "keywords_found": len(found),
            "message": f"{len(matched)} of {len(found)} keywords found in your repositories."}
