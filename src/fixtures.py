"""football-data.org'dan gerçek fikstürü çekip matches.json'u senkron eder.

Doldurduğu alanlar: kickoff (UTC + TR saatli gösterim), status, result,
matchday, fd_id ve kanonik ev/deplasman sırası (API otoritedir).
Tek API çağrısı yapar — günlük cron için throttle dostu.

Kullanım:  python src/fixtures.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from build_data import TR
from footballdata import fetch_group_matches

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "matches.json")
TR_TZ = ZoneInfo("Europe/Istanbul")
TR_MONTHS = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz",
             "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]

STATUS_MAP = {
    "FINISHED": "finished", "AWARDED": "finished",
    "IN_PLAY": "live", "PAUSED": "live",
}


def tr_display(utc: str | None) -> str | None:
    """'2026-06-11T19:00:00Z' -> '11 Haz 22:00' (TR saati)."""
    if not utc:
        return None
    dt = datetime.fromisoformat(utc.replace("Z", "+00:00")).astimezone(TR_TZ)
    return f"{dt.day} {TR_MONTHS[dt.month]} {dt:%H:%M}"


def sync() -> dict:
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)

    # API kayıtlarını sırasız çift anahtarıyla indeksle
    api = {frozenset((r["home_en"], r["away_en"])): r for r in fetch_group_matches()}

    matched = 0
    for m in data["matches"]:
        rec = api.get(frozenset((m["home_en"], m["away_en"])))
        if not rec:
            continue
        matched += 1
        # Kanonik ev/deplasman sırası: API otoritedir
        m["home_en"], m["away_en"] = rec["home_en"], rec["away_en"]
        m["home"], m["away"] = TR.get(rec["home_en"], rec["home_en"]), TR.get(rec["away_en"], rec["away_en"])
        m["matchday"] = rec["matchday"] or m["matchday"]
        m["kickoff"] = rec["utc"]
        m["kickoff_tr"] = tr_display(rec["utc"])
        m["fd_id"] = rec["fd_id"]
        m["status"] = STATUS_MAP.get(rec["status"], "scheduled")
        m["result"] = rec["result"]

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return {"total": len(data["matches"]), "matched": matched,
            "finished": sum(1 for m in data["matches"] if m["status"] == "finished")}


if __name__ == "__main__":
    s = sync()
    print(f"Senkron tamam: {s['matched']}/{s['total']} maç eşleşti, "
          f"{s['finished']} oynanmış.")
    if s["matched"] < s["total"]:
        print(f"  ⚠ {s['total'] - s['matched']} maç eşleşmedi — isim/sıra kontrolü gerekebilir.")
