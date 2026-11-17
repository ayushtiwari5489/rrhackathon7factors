"""Build a self-contained HTML dashboard from the ranking CSV files."""
import csv
import json
import os


def build_dashboard(out_dir, top=10):
    """Create a dashboard that can be opened locally without a web server."""
    data = {}
    for role, filename in (("bat", "ranking_batters.csv"), ("bowl", "ranking_bowlers.csv")):
        path = os.path.join(out_dir, filename)
        with open(path, newline="", encoding="utf-8-sig") as file:
            data[role] = list(csv.DictReader(file))

    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    page = _HTML.replace("__RANKING_DATA__", payload).replace("__DEFAULT_TOP__", str(max(1, top)))
    dashboard_path = os.path.abspath(os.path.join(out_dir, "dashboard.html"))
    with open(dashboard_path, "w", encoding="utf-8") as file:
        file.write(page)
    return dashboard_path


_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#101a30">
<title>Cricket rankings dashboard</title>
<style>
:root{color-scheme:dark;--bg:#0b1220;--panel:#111c30;--panel2:#17243a;--line:#25334a;--muted:#91a0b7;--text:#f4f7fb;--lime:#c8f169;--blue:#8eb8ff;--orange:#ffc47a}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 10% 0%,#1d304b 0,transparent 38%),var(--bg);color:var(--text);font:15px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.wrap{max-width:1440px;margin:auto;padding:38px 30px 60px}.eyebrow{color:var(--lime);font-size:12px;font-weight:800;letter-spacing:.15em;text-transform:uppercase}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:24px;margin-bottom:28px}h1{font-size:clamp(32px,5vw,54px);line-height:1.04;letter-spacing:-.05em;margin:10px 0 12px}.subtitle{color:var(--muted);margin:0}
.switch{display:flex;gap:8px;padding:5px;border:1px solid var(--line);border-radius:14px;background:#0d1728}
button,select,input{font:inherit;color:var(--text)}button{cursor:pointer}.role{border:0;background:transparent;color:var(--muted);font-weight:750;border-radius:10px;padding:10px 16px}.role.active{background:var(--lime);color:#15200a}
.cards{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:26px 0}.card,.panel{background:linear-gradient(145deg,rgba(23,36,58,.96),rgba(15,26,44,.96));border:1px solid var(--line);border-radius:18px}.card{padding:18px 20px}.label{color:var(--muted);font-size:12px;font-weight:700;letter-spacing:.07em;text-transform:uppercase}.value{font-size:27px;font-weight:800;letter-spacing:-.04em;margin-top:7px}.hint{color:var(--muted);font-size:12px;margin-top:2px}
.grid{display:grid;grid-template-columns:minmax(0,1.35fr) minmax(300px,.8fr);gap:14px}.panel{padding:22px}.panel h2{font-size:17px;margin:0 0 4px;letter-spacing:-.02em}.description{color:var(--muted);font-size:13px;margin:0 0 18px}.chart{display:grid;gap:12px}.bar-row{display:grid;grid-template-columns:minmax(90px,155px) 1fr 44px;align-items:center;gap:12px;font-size:13px}.bar-name{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.bar-track{height:10px;border-radius:99px;background:#26344a;overflow:hidden}.bar-fill{height:100%;border-radius:inherit;background:linear-gradient(90deg,#8eb8ff,#c8f169)}.bar-score{text-align:right;font-variant-numeric:tabular-nums;font-weight:750}
.leader{margin-top:22px;padding:14px 15px;border-radius:13px;background:rgba(200,241,105,.08);border:1px solid rgba(200,241,105,.18)}.leader-title{color:var(--lime);font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}.leader-name{font-size:20px;font-weight:800;margin-top:4px}.leader-meta{font-size:13px;color:var(--muted)}
.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:26px 0 12px}.toolbar h2{margin:0 auto 0 0;font-size:18px}.control{background:#111c30;border:1px solid var(--line);border-radius:10px;padding:9px 12px}.control:focus{outline:2px solid var(--blue);outline-offset:1px}input.control{width:min(280px,100%)}.count{color:var(--muted);font-size:13px;min-width:80px;text-align:right}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:16px;background:rgba(17,28,48,.85)}table{border-collapse:collapse;width:100%;min-width:920px;text-align:left}th,td{padding:12px 14px;border-bottom:1px solid rgba(37,51,74,.72);white-space:nowrap}th{position:sticky;top:0;background:#17243a;color:#aab8cd;text-transform:uppercase;letter-spacing:.07em;font-size:10px;z-index:1;cursor:pointer}th:hover{color:var(--lime)}tbody tr:hover{background:rgba(142,184,255,.07)}tbody tr:last-child td{border-bottom:0}.rank{color:var(--muted);font-variant-numeric:tabular-nums}.player{font-weight:750}.rating{display:inline-flex;align-items:center;gap:8px;font-weight:800;font-variant-numeric:tabular-nums}.rating-dot{width:7px;height:7px;border-radius:50%;background:var(--lime);box-shadow:0 0 12px rgba(200,241,105,.6)}.num{font-variant-numeric:tabular-nums}.empty{color:var(--muted);padding:30px;text-align:center}.foot{color:var(--muted);font-size:12px;margin-top:14px}
@media(max-width:850px){.wrap{padding:25px 16px 40px}header{align-items:flex-start;flex-direction:column}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}}
@media(max-width:430px){.cards{gap:9px}.card{padding:14px}.value{font-size:23px}.panel{padding:17px}.bar-row{grid-template-columns:90px 1fr 38px;gap:8px}}
</style>
</head>
<body>
<main class="wrap">
  <header>
    <div><div class="eyebrow">Cricket analytics · player ratings</div><h1>Rankings, in focus.</h1><p class="subtitle">A data-led look at the players setting the standard.</p></div>
    <nav class="switch" aria-label="Player type">
      <button class="role active" data-role="bat" aria-pressed="true">Batters</button>
      <button class="role" data-role="bowl" aria-pressed="false">Bowlers</button>
    </nav>
  </header>
  <section class="cards" aria-label="Ranking summary">
    <article class="card"><div class="label">Players ranked</div><div class="value" id="players">—</div><div class="hint">qualified for the ranking pool</div></article>
    <article class="card"><div class="label">Top rating</div><div class="value" id="top-rating">—</div><div class="hint" id="top-name">highest overall score</div></article>
    <article class="card"><div class="label">Pool average</div><div class="value" id="average">—</div><div class="hint">overall rating · 50 is average</div></article>
    <article class="card"><div class="label">Matches covered</div><div class="value" id="matches">—</div><div class="hint">combined appearances in pool</div></article>
  </section>
  <section class="grid">
    <article class="panel"><h2>Top performers</h2><p class="description">Overall ratings for the leading eight players</p><div class="chart" id="chart"></div></article>
    <aside class="panel"><h2>Leaderboard</h2><p class="description">The current number-one ranked player</p><div class="leader" id="leader"></div><p class="description" style="margin:15px 0 0">Ratings combine recent form, pressure performance, opposition, match impact and role-specific skills. Missing factors are excluded rather than scored as zero.</p></aside>
  </section>
  <section>
    <div class="toolbar"><h2>Full rankings</h2><input id="search" class="control" type="search" placeholder="Search players…" aria-label="Search players"><select id="limit" class="control" aria-label="Rows to show"><option value="10">Top 10</option><option value="25">Top 25</option><option value="50">Top 50</option><option value="all">All players</option></select><span id="count" class="count"></span></div>
    <div class="table-wrap"><table><thead><tr id="head"></tr></thead><tbody id="rows"></tbody></table><div id="empty" class="empty" hidden>No players match your search.</div></div>
    <p class="foot">Select a column heading to sort. Ratings are on a 0–100 scale; larger scores indicate stronger performance.</p>
  </section>
</main>
<script>
const rankingData = __RANKING_DATA__;
const columns = [
  ["rank","Rank"],["player","Player"],["overall_rating","Rating"],["matches","Matches"],["balls","Balls"],
  ["recent_consistency","Recent form"],["pressure_collapse","Pressure"],["opposition_strength","Opposition"],
  ["big_match","Big match"],["scoring_quality","Scoring quality"],["control","Control"],
  ["pace_spin_balance","Pace / spin"],["wicket_taking","Wicket taking"],
  ["setting_chasing_balance","Batting order"],["left_right_balance","Left / right"],["phase_skill","Phase skill"],["last_match","Last match"]
];
let role = "bat", sortKey = "rank", sortDirection = 1;
const number = value => value === "" || value == null ? NaN : Number(value);
const format = value => Number.isFinite(number(value)) ? Number(value).toLocaleString(undefined,{maximumFractionDigits:1}) : "—";
const text = value => String(value ?? "");
const defaultTop = "__DEFAULT_TOP__";
const limitSelect = document.getElementById("limit");
if (![...limitSelect.options].some(option => option.value === defaultTop)) {
  const option = document.createElement("option"); option.value=defaultTop; option.textContent=`Top ${defaultTop}`; limitSelect.add(option);
}
limitSelect.value = defaultTop;
function update() {
  const all = rankingData[role] || [];
  const query = document.getElementById("search").value.trim().toLocaleLowerCase();
  const filtered = all.filter(row => text(row.player).toLocaleLowerCase().includes(query));
  const sorted = [...filtered].sort((a,b) => {
    const av = number(a[sortKey]), bv = number(b[sortKey]);
    const cmp = Number.isFinite(av) && Number.isFinite(bv) ? av-bv : text(a[sortKey]).localeCompare(text(b[sortKey]));
    return cmp * sortDirection;
  });
  const limit = document.getElementById("limit").value;
  const visible = limit === "all" ? sorted : sorted.slice(0,Number(limit));
  const first = all[0];
  document.getElementById("players").textContent = all.length.toLocaleString();
  document.getElementById("top-rating").textContent = first ? format(first.overall_rating) : "—";
  document.getElementById("top-name").textContent = first ? text(first.player) : "no ranking data";
  document.getElementById("average").textContent = all.length ? format(all.reduce((sum,row) => sum + (number(row.overall_rating)||0),0)/all.length) : "—";
  document.getElementById("matches").textContent = all.reduce((sum,row) => sum + (number(row.matches)||0),0).toLocaleString();
  document.getElementById("leader").innerHTML = first
    ? `<div class="leader-title">#1 ${role === "bat" ? "batter" : "bowler"}</div><div class="leader-name">${escapeHtml(text(first.player))}</div><div class="leader-meta">${format(first.overall_rating)} overall rating · ${format(first.matches)} matches</div>`
    : '<div class="leader-meta">No ranking data available.</div>';
  document.getElementById("chart").innerHTML = all.slice(0,8).map(row => {
    const score = number(row.overall_rating)||0;
    return `<div class="bar-row"><div class="bar-name" title="${escapeHtml(text(row.player))}">${escapeHtml(text(row.player))}</div><div class="bar-track"><div class="bar-fill" style="width:${Math.max(0,Math.min(100,score))}%"></div></div><div class="bar-score">${format(score)}</div></div>`;
  }).join("") || '<div class="empty">No ranking data available.</div>';
  const head = document.getElementById("head");
  head.innerHTML = "";
  columns.filter(([key]) => all.some(row => Object.prototype.hasOwnProperty.call(row,key))).forEach(([key,label]) => {
    const th = document.createElement("th");
    th.textContent = label + (sortKey === key ? (sortDirection === 1 ? " ↑" : " ↓") : "");
    th.scope = "col";
    th.addEventListener("click", () => { if (sortKey === key) sortDirection *= -1; else {sortKey=key;sortDirection=1;} update(); });
    head.appendChild(th);
  });
  const body = document.getElementById("rows");
  body.innerHTML = "";
  visible.forEach(row => {
    const tr = document.createElement("tr");
    columns.filter(([key]) => all.some(item => Object.prototype.hasOwnProperty.call(item,key))).forEach(([key]) => {
      const td = document.createElement("td");
      if (key === "overall_rating") td.innerHTML = `<span class="rating"><i class="rating-dot"></i>${format(row[key])}</span>`;
      else { td.textContent = key === "rank" ? `#${format(row[key])}` : format(row[key]); if (key === "rank") td.className="rank"; if (key === "player") td.className="player"; if (["matches","balls","recent_consistency","pressure_collapse","opposition_strength","big_match"].includes(key)) td.className="num"; }
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
  document.getElementById("count").textContent = `${visible.length.toLocaleString()} of ${filtered.length.toLocaleString()}`;
  document.getElementById("empty").hidden = visible.length > 0;
}
function escapeHtml(value) { return value.replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char])); }
document.querySelectorAll(".role").forEach(button => button.addEventListener("click", () => {
  role = button.dataset.role;
  document.querySelectorAll(".role").forEach(item => {const active=item===button;item.classList.toggle("active",active);item.setAttribute("aria-pressed",String(active));});
  update();
}));
document.getElementById("search").addEventListener("input", update);
document.getElementById("limit").addEventListener("change", update);
update();
</script>
</body>
</html>
"""
