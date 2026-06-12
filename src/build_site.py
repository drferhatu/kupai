"""matches.json'dan KupAI statik sitesini (açık tema, TR/EN iki dilli) üretir.

İki dil HTML'e gömülür; üstteki TR|EN düğmesi data-tr/data-en niteliklerini
değiştirerek anında çevirir. Varsayılan dil TR; tercih localStorage'da saklanır.
Sıfır bağımlılık: yalnızca standart kütüphane.
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from scoring import outcome, score_prediction

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "..", "data", "matches.json")
OUT_DIR = os.path.join(HERE, "..", "site")

TR_TZ = ZoneInfo("Europe/Istanbul")
TR_MONTHS = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz",
             "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
EN_MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

PLAYER_LABELS = {"chatgpt": "ChatGPT", "claude": "Claude", "gemini": "Gemini", "ferhat": "Ferhat"}
PLAYER_COLORS = {"chatgpt": "#10a37f", "claude": "#d97757", "gemini": "#4285f4", "ferhat": "#c89b1a"}
PTS_COLOR = {3: "#16a34a", 2: "#2563eb", 1: "#d97706", 0: "#dc2626"}

# Instagram kredisi (üst + alt). İki dilli: TR "@... tarafından hazırlanmıştır",
# EN "Created by @...". İmza linki ve logo (inline SVG) sabit kalır.
IG_SVG = (
    '<svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor" '
    'aria-hidden="true" style="vertical-align:-2px"><path d="M12 2.16c3.2 0 3.58.01 '
    '4.85.07 1.17.05 1.8.25 2.22.41.56.22.96.48 1.38.9.42.42.68.82.9 1.38.16.42.36 '
    '1.05.41 2.22.06 1.27.07 1.65.07 4.85s-.01 3.58-.07 4.85c-.05 1.17-.25 1.8-.41 '
    '2.22-.22.56-.48.96-.9 1.38-.42.42-.82.68-1.38.9-.42.16-1.05.36-2.22.41-1.27.06-1.65.07-4.85.07'
    's-3.58-.01-4.85-.07c-1.17-.05-1.8-.25-2.22-.41-.56-.22-.96-.48-1.38-.9-.42-.42-.68-.82-.9-1.38'
    '-.16-.42-.36-1.05-.41-2.22-.06-1.27-.07-1.65-.07-4.85s.01-3.58.07-4.85c.05-1.17.25-1.8.41-2.22'
    '.22-.56.48-.96.9-1.38.42-.42.82-.68 1.38-.9.42-.16 1.05-.36 2.22-.41 1.27-.06 1.65-.07 4.85-.07'
    'M12 0C8.74 0 8.33.01 7.05.07 5.78.13 4.9.33 4.14.63c-.79.3-1.46.7-2.13 1.37C1.34 2.67.94 3.34.63 '
    '4.14.33 4.9.13 5.78.07 7.05.01 8.33 0 8.74 0 12s.01 3.67.07 4.95c.06 1.27.26 2.15.56 2.91.31.8.71 '
    '1.47 1.38 2.14.67.67 1.34 1.07 2.13 1.37.76.3 1.64.5 2.91.56C8.33 23.99 8.74 24 12 24s3.67-.01 '
    '4.95-.07c1.27-.06 2.15-.26 2.91-.56.8-.31 1.47-.71 2.14-1.38.67-.67 1.07-1.34 1.37-2.13.3-.76.5-1.64.56-2.91'
    'C23.99 15.67 24 15.26 24 12s-.01-3.67-.07-4.95c-.06-1.27-.26-2.15-.56-2.91-.31-.8-.71-1.47-1.38-2.14'
    '-.67-.67-1.34-1.07-2.13-1.37-.76-.3-1.64-.5-2.91-.56C15.67.01 15.26 0 12 0zm0 5.84A6.16 6.16 0 1 0 '
    '18.16 12 6.16 6.16 0 0 0 12 5.84zm0 10.16A4 4 0 1 1 16 12a4 4 0 0 1-4 4zm6.41-11.85a1.44 1.44 0 1 0 '
    '1.44 1.44 1.44 1.44 0 0 0-1.44-1.44z"/></svg>'
)
CREDIT = (
    '<div class="credit">'
    '<span data-tr="" data-en="Created by "></span>'
    '<a class="ig" href="https://instagram.com/dr.ferhatucar" target="_blank" rel="noopener">'
    f'{IG_SVG} @dr.ferhatucar</a>'
    '<span data-tr=" tarafından hazırlanmıştır" data-en=""> tarafından hazırlanmıştır</span>'
    '</div>'
)


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def t(tr: str, en: str, cls: str = "") -> str:
    """İki dilli inline metin; varsayılan TR gösterir."""
    c = f' class="{cls}"' if cls else ""
    return f'<span{c} data-tr="{esc(tr)}" data-en="{esc(en)}">{esc(tr)}</span>'


def fmt_dates(utc):
    """UTC ISO -> (TR gösterim, EN gösterim). İkisi de TR saat dilimi."""
    if not utc:
        return "", ""
    dt = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(TR_TZ)
    return (f"{dt.day} {TR_MONTHS[dt.month]} {dt:%H:%M}",
            f"{dt.day} {EN_MONTHS[dt.month]} {dt:%H:%M}")


def winner_label(home_tr, home_en, away_tr, away_en, h, a):
    """(tr, en) galip etiketi."""
    o = outcome(h, a)
    if o == "H":
        return home_tr, home_en
    if o == "A":
        return away_tr, away_en
    return "Beraberlik", "Draw"


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
    htr, hen = m["home"], m["home_en"]
    atr, aen = m["away"], m["away_en"]
    finished = m["status"] == "finished" and m["result"]
    dtr, den = fmt_dates(m.get("kickoff"))

    if finished:
        rh, ra = m["result"]["home"], m["result"]["away"]
        wtr, wen = winner_label(htr, hen, atr, aen, rh, ra)
        res_html = (f'<div class="score">{rh}-{ra}</div>'
                    f'<div class="sub">{t(wtr, wen)}</div>')
    else:
        res_html = '<div class="score muted">—</div>'

    cells = []
    for p in players:
        pred = m["predictions"].get(p)
        if not pred:
            cells.append('<td class="pred empty">—</td>')
            continue
        ph, pa = pred["home"], pred["away"]
        wtr, wen = winner_label(htr, hen, atr, aen, ph, pa)
        badge = ""
        if finished:
            pts = score_prediction(ph, pa, rh, ra)
            badge = f'<span class="badge" style="background:{PTS_COLOR[pts]}">{pts}P</span>'
        cells.append(f'<td class="pred"><div class="wl">{t(wtr, wen)}</div>'
                     f'<div class="sc">{ph}-{pa} {badge}</div></td>')

    g = m["group"]
    return (
        f'<tr data-group="{g}">'
        f'<td class="match"><div class="teams">{t(htr, hen, "t")}'
        f'<span class="vs">—</span>{t(atr, aen, "t")}</div>'
        f'<div class="kick">{t(dtr, den)}</div></td>'
        f'<td class="round">{t("Grup " + g, "Group " + g)}'
        f'<span class="md">{t(f"{m["matchday"]}. tur", f"Matchday {m["matchday"]}")}</span></td>'
        f'<td class="result">{res_html}</td>'
        f'{"".join(cells)}</tr>'
    )


def render(data: dict) -> str:
    players = data["players"]
    lb = compute_leaderboard(data)

    lb_html = []
    for i, r in enumerate(lb, start=1):
        c = PLAYER_COLORS[r["id"]]
        lb_html.append(
            f'<div class="lb-row">'
            f'<span class="rank">{i}.</span>'
            f'<span class="dot" style="background:{c}"></span>'
            f'<span class="name">{PLAYER_LABELS[r["id"]]}</span>'
            f'<span class="pts">{r["pts"]} <small>{t("puan", "pts")}</small></span>'
            f'<span class="avg">{r["avg"]:.2f} {t("/ maç", "/ game")}</span>'
            f'</div>'
        )

    groups = sorted({m["group"] for m in data["matches"]})
    opts = (f'<option value="all" data-tr="Tüm Gruplar" data-en="All Groups">Tüm Gruplar</option>'
            + "".join(f'<option value="{g}" data-tr="Grup {g}" data-en="Group {g}">Grup {g}</option>'
                      for g in groups))

    head_players = "".join(f'<th>{PLAYER_LABELS[p]}</th>' for p in players)
    ordered = sorted(data["matches"], key=lambda m: (m.get("kickoff") or "9999", m["group"]))
    rows = "".join(render_row(m, players) for m in ordered)

    total = len(data["matches"])
    played = sum(1 for m in data["matches"] if m["status"] == "finished")

    return TEMPLATE.format(
        tagline=t("KupAI ile Dünya Kupası'nda yapay zekâ modellerine karşı yarışıyorum",
                  "Taking on every AI at predicting the 2026 World Cup"),
        credit=CREDIT,
        th_match=t("Maç", "Match"), th_group=t("Grup", "Group"), th_result=t("Sonuç", "Result"),
        leaderboard="".join(lb_html),
        options=opts,
        head_players=head_players,
        rows=rows,
        footer=t(f"KupAI · {played}/{total} maç oynandı · veriler her gün güncellenir",
                 f"KupAI · {played}/{total} matches played · updated daily"),
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
  .lang {{ display:flex; justify-content:flex-end; gap:4px; padding-top:4px; }}
  .lang-btn {{ border:1px solid var(--line); background:var(--card); color:var(--muted);
    font-size:12px; font-weight:700; padding:4px 10px; border-radius:8px; cursor:pointer; }}
  .lang-btn.active {{ background:var(--ink); color:#fff; border-color:var(--ink); }}
  header {{ text-align:center; padding:8px 0; }}
  .trophy {{ font-size:44px; }}
  h1 {{ font-size:40px; margin:6px 0 4px; letter-spacing:-1px; font-weight:800; }}
  h1 .ai {{ color:var(--accent); }}
  .tag {{ color:var(--muted); font-size:15px; max-width:540px; margin:0 auto; }}
  .credit {{ color:var(--muted); font-size:13px; margin-top:8px; }}
  .credit a.ig {{ color:var(--accent); text-decoration:none; font-weight:700;
    display:inline-flex; align-items:center; gap:4px; }}
  .credit a.ig:hover {{ text-decoration:underline; }}
  footer .credit {{ margin-top:6px; }}
  .section-title {{ font-size:13px; letter-spacing:2px; color:var(--muted);
    text-transform:uppercase; font-weight:700; margin:32px 4px 12px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    box-shadow:0 1px 3px rgba(20,30,50,.04); overflow:hidden; }}
  .lb-row {{ display:flex; align-items:center; gap:12px; padding:16px 18px;
    border-bottom:1px solid var(--line); }}
  .lb-row:last-child {{ border-bottom:0; }}
  .rank {{ font-weight:800; color:var(--muted); width:28px; }}
  .dot {{ width:12px; height:12px; border-radius:50%; flex:0 0 auto; }}
  .name {{ font-weight:700; font-size:17px; flex:1; }}
  .pts {{ font-weight:800; font-size:18px; }}
  .pts small {{ font-weight:600; color:var(--muted); font-size:12px; }}
  .avg {{ color:var(--muted); font-size:13px; width:104px; text-align:right;
    font-variant-numeric:tabular-nums; }}
  .rule {{ display:flex; align-items:center; gap:10px; padding:13px 18px;
    border-bottom:1px solid var(--line); }}
  .rule:last-child {{ border-bottom:0; }}
  .rule .d {{ width:11px; height:11px; border-radius:50%; }}
  .rule .txt {{ flex:1; }}
  .rule .p {{ font-weight:800; }}
  .toolbar {{ margin:0 4px 12px; }}
  select {{ font-size:15px; padding:9px 12px; border:1px solid var(--line);
    border-radius:10px; background:var(--card); color:var(--ink); }}
  .table-scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
  table {{ border-collapse:collapse; width:100%; min-width:720px; font-size:13px; }}
  thead th {{ text-align:left; padding:12px 12px; color:var(--muted);
    font-size:11px; letter-spacing:1px; text-transform:uppercase;
    border-bottom:1px solid var(--line); white-space:nowrap; }}
  tbody td {{ padding:11px 12px; border-bottom:1px solid var(--line); vertical-align:middle; }}
  tbody tr:hover {{ background:#fafbfc; }}
  td.match .t {{ font-weight:700; }}
  td.match .vs {{ color:var(--muted); margin:0 6px; }}
  td.match .kick {{ font-size:11px; color:var(--muted); margin-top:3px; }}
  td.round {{ color:var(--muted); white-space:nowrap; }}
  td.round .md {{ display:block; font-size:11px; opacity:.8; }}
  td.result .score {{ font-weight:800; font-size:15px; font-variant-numeric:tabular-nums; }}
  td.result .score.muted {{ color:var(--line); }}
  td.result .sub {{ font-size:11px; color:var(--muted); }}
  td.pred {{ font-variant-numeric:tabular-nums; }}
  td.pred.empty {{ color:var(--line); text-align:center; }}
  td.pred .wl {{ font-weight:600; }}
  td.pred .sc {{ color:var(--muted); display:flex; align-items:center; gap:6px; }}
  .badge {{ color:#fff; font-size:10px; font-weight:800; padding:1px 6px; border-radius:6px; }}
  footer {{ text-align:center; color:var(--muted); font-size:12px; margin-top:36px; }}
  @media (max-width:560px) {{ h1 {{ font-size:32px; }} .avg {{ display:none; }} }}
</style>
</head>
<body>
<div class="wrap">
  <div class="lang">
    <button class="lang-btn" data-lang="tr" onclick="setLang('tr')">TR</button>
    <button class="lang-btn" data-lang="en" onclick="setLang('en')">EN</button>
  </div>
  <header>
    <div class="trophy">🏆</div>
    <h1>Kup<span class="ai">AI</span></h1>
    <p class="tag">{tagline}</p>
    {credit}
  </header>

  <div class="section-title" data-tr="Liderlik Tablosu" data-en="Leaderboard">Liderlik Tablosu</div>
  <div class="card">{leaderboard}</div>

  <div class="section-title" data-tr="Puanlama" data-en="Scoring">Puanlama</div>
  <div class="card">
    <div class="rule"><span class="d" style="background:#16a34a"></span>
      <span class="txt" data-tr="Doğru galip + tam skor" data-en="Correct winner + exact score">Doğru galip + tam skor</span>
      <span class="p" data-tr="3 puan" data-en="3 pts">3 puan</span></div>
    <div class="rule"><span class="d" style="background:#2563eb"></span>
      <span class="txt" data-tr="Doğru galip + doğru gol farkı" data-en="Correct winner + correct goal difference">Doğru galip + doğru gol farkı</span>
      <span class="p" data-tr="2 puan" data-en="2 pts">2 puan</span></div>
    <div class="rule"><span class="d" style="background:#d97706"></span>
      <span class="txt" data-tr="Doğru galip (sadece)" data-en="Correct winner only">Doğru galip (sadece)</span>
      <span class="p" data-tr="1 puan" data-en="1 pt">1 puan</span></div>
    <div class="rule"><span class="d" style="background:#dc2626"></span>
      <span class="txt" data-tr="Yanlış galip" data-en="Wrong winner">Yanlış galip</span>
      <span class="p" data-tr="0 puan" data-en="0 pts">0 puan</span></div>
  </div>

  <div class="section-title" data-tr="Tahminler &amp; Sonuçlar" data-en="Predictions &amp; Results">Tahminler &amp; Sonuçlar</div>
  <div class="toolbar">
    <select id="groupFilter" onchange="filterGroup(this.value)">{options}</select>
  </div>
  <div class="card table-scroll">
    <table>
      <thead><tr>
        <th>{th_match}</th><th>{th_group}</th><th>{th_result}</th>{head_players}
      </tr></thead>
      <tbody id="rows">{rows}</tbody>
    </table>
  </div>

  <footer>{footer}{credit}</footer>
</div>
<script>
  function filterGroup(g) {{
    document.querySelectorAll('#rows tr').forEach(function(tr) {{
      tr.style.display = (g === 'all' || tr.dataset.group === g) ? '' : 'none';
    }});
  }}
  function setLang(lang) {{
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-tr]').forEach(function(el) {{
      var v = el.getAttribute('data-' + lang);
      if (v !== null) el.textContent = v;
    }});
    document.querySelectorAll('.lang-btn').forEach(function(b) {{
      b.classList.toggle('active', b.getAttribute('data-lang') === lang);
    }});
    try {{ localStorage.setItem('kupai_lang', lang); }} catch (e) {{}}
  }}
  (function() {{
    var saved = 'tr';
    try {{ saved = localStorage.getItem('kupai_lang') || 'tr'; }} catch (e) {{}}
    setLang(saved);
  }})();
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
    print(f"site/index.html yazıldı ({len(data['matches'])} maç, TR/EN).")


if __name__ == "__main__":
    main()
