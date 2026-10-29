// The server does all calculations. This file only fetches JSON and draws it.
const $ = (id) => document.getElementById(id);
const PALETTE = ["#1f4a8a", "#4b7bc0", "#84a9d9", "#2f8f83", "#d08a2e", "#a3556b", "#8a93a3"];
const SOURCES = { cache: "saved copy", github: "GitHub just now", stale: "saved copy (GitHub unreachable)" };
let pie;

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (res.status === 422) throw new Error("Paste a longer job description (at least 20 characters).");
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : `Request failed (${res.status})`);
  return body;
}

function setStatus(text, isError = false) {
  $("status").textContent = text;
  $("status").className = isError ? "error" : "";
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderBadge(vibe) {
  $("badge").dataset.band = vibe ? vibe.band : "none";
  $("badge-num").textContent = vibe ? `${vibe.match_percentage}%` : "–";
}

function renderPie(langs) {
  if (pie) pie.destroy();
  if (!window.Chart || !langs.length) return;
  pie = new Chart($("pie"), {
    type: "pie",
    data: {
      labels: langs.map((l) => `${l.language} (${l.percent}%)`),
      datasets: [{ data: langs.map((l) => l.count), backgroundColor: PALETTE, borderWidth: 1 }],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { position: "right" } } },
  });
}

function renderHeatmap(h) {
  const grid = $("heatmap");
  grid.replaceChildren();
  for (const week of h.weeks) {
    for (const cell of week) {
      const div = el("div", cell ? `cell l${cell.level}` : "cell pad");
      if (cell) div.title = `${cell.count} contribution${cell.count === 1 ? "" : "s"} on ${cell.date}`;
      grid.append(div);
    }
  }
  $("heat-note").textContent = `${h.total} contributions in the last year.` +
    (h.approximate ? " Approximate: no GitHub token, so this uses recent public events only." : "");
}

function renderRepos(repos) {
  const box = $("repos");
  box.replaceChildren();
  if (!repos.length) box.append(el("p", "muted", "No public repositories yet."));
  for (const r of repos) {
    const card = el("article", "card");
    const link = el("a", "", r.name);
    link.href = r.url; link.target = "_blank"; link.rel = "noopener";
    const title = el("h3"); title.append(link);
    const meta = el("div", "meta");
    if (r.language) { const l = el("span", "", r.language); l.prepend(el("i", "dot")); meta.append(l); }
    meta.append(el("span", "", `★ ${r.stars}`), el("span", "", `Forks ${r.forks}`));
    card.append(title, el("p", "", r.description || "No description."), meta);
    box.append(card);
  }
}

function renderProfile(p) {
  $("app").hidden = false;
  $("avatar").src = p.avatar_url;
  $("name").textContent = p.name;
  $("bio").textContent = p.bio || "";
  $("followers").textContent = p.followers;
  $("stars").textContent = p.total_stars;
  $("repo-count").textContent = p.public_repos;
  $("cur-streak").textContent = `${p.heatmap.current_streak} days`;
  $("long-streak").textContent = `${p.heatmap.longest_streak} days`;
  $("jd").value = p.last_job_description || "";
  renderBadge(p.vibe);
  $("vibe-result").replaceChildren();
  renderPie(p.top_languages);
  renderHeatmap(p.heatmap);
  renderRepos(p.repos);
  setStatus(`Loaded from ${SOURCES[p.cache.source]}. Last updated ${new Date(p.cache.fetched_at).toLocaleString()}.`);
}

async function loadProfile(refresh = false) {
  const user = $("user").value.trim();
  if (!user) return;
  setStatus("Loading…");
  try {
    renderProfile(await api(`/api/profile/${encodeURIComponent(user)}${refresh ? "?refresh=true" : ""}`));
  } catch (err) {
    setStatus(err.message, true);
  }
}

function chips(title, items, cls) {
  const wrap = el("div");
  wrap.append(el("strong", "", title));
  const row = el("div", "chips");
  for (const item of items) row.append(el("span", `chip ${cls}`, item));
  wrap.append(row);
  return wrap;
}

async function checkMatch(event) {
  event.preventDefault();
  const box = $("vibe-result");
  try {
    const r = await api("/api/vibe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: $("user").value.trim(), job_description: $("jd").value }),
    });
    renderBadge(r);
    box.replaceChildren(el("p", "muted", r.message));
    if (r.matched.length) box.append(chips("In your repositories", r.matched, "hit"));
    if (r.missing.length) box.append(chips("Not found yet", r.missing, "miss"));
  } catch (err) {
    box.replaceChildren(el("p", "error", err.message));
  }
}

$("lookup").addEventListener("submit", (e) => { e.preventDefault(); loadProfile(); });
$("refresh").addEventListener("click", () => loadProfile(true));
$("vibe-form").addEventListener("submit", checkMatch);
