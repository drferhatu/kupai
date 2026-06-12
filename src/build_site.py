"""matches.json'dan KupAI statik sitesini (açık tema) üretir -> site/index.html.

Sıfır bağımlılık: yalnızca standart kütüphane. Puanları scoring.py ile hesaplar,
liderlik tablosu + puanlama kuralı + grup filtreli tahmin tablosunu render eder.
"""

from __future__ import annotations

import html
import json
import os

from scoring import outcome, score_prediction

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data", "matches.json")
OUT_DIR = os.path.join(HERE, "..", "site")

PLAYER_LABELS = {"chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini", "ferhat": "Ferhat"}
PLAYER_COLORS = {"chatgpt": "#10a37f", "claude": "#d97757", "gemini": "#4285f4", "ferhat": "#c89b1a"}
PTS_COLOR = {3: "#16a34a", 2: "#2563eb", 1: "#d97706", 0: "#dc2626"}
RANK_TR = {1: "1.", 2: "2.", 3: "3.", 4: "4."}


def winner_label(home_team: str, away_team: str, h: int, a: int) -> str:
    o = outcome(h, a)
    return {"H": home_team, "A": away_team, "D": "Beraberlik"}[o]


def compute_leaderboard(data: dict):
    totals = {p: 0 for p in data["players"]}
    games = {p: 0 for p in data["players"]}
    for m in data["matches"]:
        if m["status"] != "finished" or not m["result"]:
            continue
        rh, ra = m["result"]["home"], m["result"]["away"]
        for p in data["players"]:
            pred = m["predictions"].get(p)
            if not pred:
                continue
            totals[p] += score_prediction(pred["home"], pred["away"], rh, ra)
            games[p] += 1
    rows = []
    for p in data["players"]:
        avg = totals[p] / games[p] if games[p] else 0.0
        rows.append({"id": p, "pts": totals[p], "games": games[p], "avg": avg})
    rows.sort(key=lambda r: (-r["pts"], -r["avg"], r["id"]))
    return rows


def render_row(m: dict, players) -> str:
    home, away = html.escape(m["home"]), html.escape(m["away"])
    finished = m["status"] == "finished" and m["result"]
    if finished:
        rh, ra = m["result"]["home"], m["result"]["away"]
        res_html = (f'<div class="score">{rh}-{ra}</div>'
                    f'<div class="sub">{html.escape(winner_label(home, away, rh, ra))}</div>')
    else:
        res_html = '<div class="score muted">—</div>'

    cells = []
    for p in players:
        pred = m["predictions"].get(p)
        if not pred:
            cells.append('<td class="pred empty">—</td>')
            continue
        ph, pa = pred["home"], pred["away"]
        wl = html.escape(winner_label(home, away, ph, pa))
        badge = ""
        if finished:
            pts = score_prediction(ph, pa, rh, ra)
            badge = f'<span class="badge" style="background:{PTS_COLOR[pts]}">{pts}P</span>'
        cells.append(f'<td class="pred"><div class="wl">{wl}</div>'
                     f'<div class="sc">{ph}-{pa} {badge}</div></td>')

    kick = html.escape(m.get("kickoff_tr") or "")
    return (
        f'<tr data-group="{m["group"]}">'
        f'<td class="match"><div class="teams"><span class="t">{home}</span>'
        f'<span class="vs">—</span><span class="t">{away}</span></div>'
        f'<div class="kick">{kick}</div></td>'
        f'<td class="round">Grup {m["group"]}<span class="md">{m["matchday"]}. tur</span></td>'
        f'<td class="result">{res_html}</td>'
        f'{"".join(cells)}</tr>'
    )


def render(data: dict) -> str:
    players = data["players"]
    lb = compute_leaderboard(data)

    # Liderlik tablosu kartları
    lb_html = []
    for i, r in enumerate(lb, start=1):
        c = PLAYER_COLORS[r["id"]]
        lb_html.append(
            f'<div class="lb-row">'
            f'<span class="rank">{RANK_TR.get(i, str(i)+".")}</span>'
            f'<span class="dot" style="background:{c}"></span>'
            f'<span class="name">{PLAYER_LABELS[r["id"]]}</span>'
            f'<span class="pts">{r["pts"]} <small>puan</small></span>'
            f'<span class="avg">{r["avg"]:.2f} / maç</span>'
            f'</div>'
        )

    # Grup filtresi seçenekleri
    groups = sorted({m["group"] for m in data["matches"]})
    opts = '<option value="all">Tüm Gruplar</option>' + "".join(
        f'<option value="{g}">Grup {g}</option>' for g in groups)

    # Tablo başlık + satırlar (kronolojik: önce kickoff'a göre)
    head_players = "".join(f'<th>{PLAYER_LABELS[p]}</th>' for p in players)
    ordered = sorted(data["matches"], key=lambda m: (m.get("kickoff") or "9999", m["group"]))
    rows = "".join(render_row(m, players) for m in ordered)

    played = sum(1 for m in data["matches"] if m["status"] == "finished")

    return TEMPLATE.format(
        tagline="KupAI ile Dünya Kupası&#39;nda yapay zekâ modellerine karşı yarışıyorum",
        leaderboard="".join(lb_html),
        options=opts,
        head_players=head_players,
        rows=rows,
        total=len(data["matches"]),
        played=played,
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KupAI — Dünya Kupası Yapay Zekâ Tahmin Yarışı</title>
<style>
  :root {{
    --bg:#f5f7fa; --card:#ffffff; --ink:#1a2233; --muted:#6b7689;
    --line:#e6e9ef; --accent:#c89b1a;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    line-height:1.5; }}
  .wrap {{ max-width:1040px; margin:0 auto; padding:24px 16px 64px; }}
  header {{ text-align:center; padding:28px 0 8px; }}
  .trophy {{ font-size:44px; }}
  h1 {{ font-size:40px; margin:6px 0 4px; letter-spacing:-1px; font-weight:800; }}
  h1 .ai {{ color:var(--accent); }}
  .tag {{ color:var(--muted); font-size:15px; max-width:520px; margin:0 auto; }}
  .section-title {{ font-size:13px; letter-spacing:2px; color:var(--muted);
    text-transform:uppercase; font-weight:700; margin:32px 4px 12px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    box-shadow:0 1px 3px rgba(20,30,50,.04); overflow:hidden; }}
  /* Liderlik */
  .lb-row {{ display:flex; align-items:center; gap:12px; padding:16px 18px;
    border-bottom:1px solid var(--line); }}
  .lb-row:last-child {{ border-bottom:0; }}
  .rank {{ font-weight:800; color:var(--muted); width:28px; }}
  .dot {{ width:12px; height:12px; border-radius:50%; flex:0 0 auto; }}
  .name {{ font-weight:700; font-size:17px; flex:1; }}
  .pts {{ font-weight:800; font-size:18px; }}
  .pts small {{ font-weight:600; color:var(--muted); font-size:12px; }}
  .avg {{ color:var(--muted); font-size:13px; width:96px; text-align:right;
    font-variant-numeric:tabular-nums; }}
  /* Puanlama */
  .rule {{ display:flex; align-items:center; gap:10px; padding:13px 18px;
    border-bottom:1px solid var(--line); }}
  .rule:last-child {{ border-bottom:0; }}
  .rule .d {{ width:11px; height:11px; border-radius:50%; }}
  .rule .txt {{ flex:1; }}
  .rule .p {{ font-weight:800; }}
  /* Tahmin tablosu */
  .toolbar {{ margin:0 4px 12px; }}
  select {{ font-size:15px; padding:9px 12px; border:1px solid var(--line);
    border-radius:10px; background:var(--card); color:var(--ink); }}
  .table-scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
  table {{ border-collapse:collapse; width:100%; min-width:720px; font-size:13px; }}
  thead th {{ text-align:left; padding:12px 12px; color:var(--muted);
    font-size:11px; letter-spacing:1px; text-transform:uppercase;
    border-bottom:1px solid var(--line); white-space:nowrap; }}
  tbody td {{ padding:11px 12px; border-bottom:1px solid var(--line);
    vertical-align:middle; }}
  tbody tr:hover {{ background:#fafbfc; }}
  td.match .t {{ font-weight:700; }}
  td.match .vs {{ color:var(--muted); margin:0 6px; }}
  td.match .kick {{ font-size:11px; color:var(--muted); margin-top:3px; }}
  td.round {{ color:var(--muted); white-space:nowrap; }}
  td.round .md {{ display:block; font-size:11px; opacity:.8; }}
  td.result .score {{ font-weight:800; font-size:15px;
    font-variant-numeric:tabular-nums; }}
  td.result .score.muted {{ color:var(--line); }}
  td.result .sub {{ font-size:11px; color:var(--muted); }}
  td.pred {{ font-variant-numeric:tabular-nums; }}
  td.pred.empty {{ color:var(--line); text-align:center; }}
  td.pred .wl {{ font-weight:600; }}
  td.pred .sc {{ color:var(--muted); display:flex; align-items:center; gap:6px; }}
  .badge {{ color:#fff; font-size:10px; font-weight:800; padding:1px 6px;
    border-radius:6px; }}
  footer {{ text-align:center; color:var(--muted); font-size:12px; margin-top:36px; }}
  @media (max-width:560px) {{
    h1 {{ font-size:32px; }} .avg {{ display:none; }}
  }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="trophy">🏆</div>
    <h1>Kup<span class="ai">AI</span></h1>
    <p class="tag">{tagline}</p>
  </header>

  <div class="section-title">Liderlik Tablosu</div>
  <div class="card">{leaderboard}</div>

  <div class="section-title">Puanlama</div>
  <div class="card">
    <div class="rule"><span class="d" style="background:#16a34a"></span>
      <span class="txt">Doğru galip + tam skor</span><span class="p">3 puan</span></div>
    <div class="rule"><span class="d" style="background:#2563eb"></span>
      <span class="txt">Doğru galip + doğru gol farkı</span><span class="p">2 puan</span></div>
    <div class="rule"><span class="d" style="background:#d97706"></span>
      <span class="txt">Doğru galip (sadece)</span><span class="p">1 puan</span></div>
    <div class="rule"><span class="d" style="background:#dc2626"></span>
      <span class="txt">Yanlış galip</span><span class="p">0 puan</span></div>
  </div>

  <div class="section-title">Tahminler &amp; Sonuçlar</div>
  <div class="toolbar">
    <select id="groupFilter" onchange="filterGroup(this.value)">{options}</select>
  </div>
  <div class="card table-scroll">
    <table>
      <thead><tr>
        <th>Maç</th><th>Grup</th><th>Sonuç</th>{head_players}
      </tr></thead>
      <tbody id="rows">{rows}</tbody>
    </table>
  </div>

  <footer>KupAI · {played}/{total} maç oynandı · veriler her gün güncellenir</footer>
</div>
<script>
  function filterGroup(g) {{
    document.querySelectorAll('#rows tr').forEach(function(tr) {{
      tr.style.display = (g === 'all' || tr.dataset.group === g) ? '' : 'none';
    }});
  }}
</script>
</body>
</html>
"""


def main():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "index.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(data))
    print(f"site/index.html yazıldı ({len(data['matches'])} maç).")


if __name__ == "__main__":
    main()
