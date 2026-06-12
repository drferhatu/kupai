"""football-data.org API istemcisi (throttle-aware) + takım adı eşleştirme.

Daniel'in (football-data) uyarısı gereği yanıt header'larındaki
'X-Requests-Available-Minute' okunur; kota bittiyse reset süresi kadar beklenir.
Böylece rate limiter'a takılmayız.
"""

from __future__ import annotations

import os
import time
import urllib.request
import json as _json

BASE = "https://api.football-data.org/v4"

# Bizim İngilizce adımız -> football-data.org'un kullandığı ad (sadece farklı olanlar)
ALIAS = {
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "Cabo Verde": "Cape Verde Islands",
    "Côte d'Ivoire": "Ivory Coast",
    "DR Congo": "Congo DR",
    "IR Iran": "Iran",
    "Korea Republic": "South Korea",
    "Türkiye": "Turkey",
    "USA": "United States",
}
# football-data adı -> bizim İngilizce adımız
REVERSE = {v: k for k, v in ALIAS.items()}


def fd_to_mine(name: str) -> str:
    """football-data takım adını bizim kanonik İngilizce adımıza çevirir."""
    return REVERSE.get(name, name)


def load_key() -> str:
    """.env'den FOOTBALL_DATA_API_KEY okur (python-dotenv'siz, basit parser)."""
    key = os.environ.get("FOOTBALL_DATA_API_KEY")
    if key:
        return key
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("FOOTBALL_DATA_API_KEY="):
                return line.split("=", 1)[1].strip()
    raise RuntimeError("FOOTBALL_DATA_API_KEY bulunamadı (.env)")


def get(path: str, key: str | None = None) -> dict:
    """API'den GET; throttle header'ına saygı gösterir."""
    key = key or load_key()
    req = urllib.request.Request(f"{BASE}{path}", headers={"X-Auth-Token": key})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = _json.loads(resp.read().decode("utf-8"))
        avail = resp.headers.get("X-Requests-Available-Minute")
        reset = resp.headers.get("X-RequestCounter-Reset")
        # Bu çağrıdan sonra kota bittiyse, bir sonraki çağrı için reset'i bekle.
        if avail is not None and int(avail) <= 0 and reset is not None:
            wait = int(reset) + 1
            print(f"  [throttle] kota doldu, {wait}sn bekleniyor…")
            time.sleep(wait)
    return data


def fetch_group_matches(key: str | None = None) -> list[dict]:
    """WC grup aşaması maçlarını normalize edilmiş kayıtlar olarak döndürür.

    Her kayıt: home_en, away_en (bizim kanonik adlarımız, API'nin ev/dep sırasıyla),
    group ('A'..'L'), matchday, utc (ISO), status (FINISHED/IN_PLAY/...),
    result ({'home','away'} ya da None), fd_id.
    """
    data = get("/competitions/WC/matches", key=key)
    out = []
    for m in data.get("matches", []):
        if m.get("stage") != "GROUP_STAGE":
            continue
        ft = (m.get("score") or {}).get("fullTime") or {}
        result = None
        if m.get("status") in ("FINISHED", "AWARDED") and ft.get("home") is not None:
            result = {"home": ft["home"], "away": ft["away"]}
        out.append({
            "home_en": fd_to_mine(m["homeTeam"]["name"]),
            "away_en": fd_to_mine(m["awayTeam"]["name"]),
            "group": (m.get("group") or "").replace("GROUP_", ""),
            "matchday": m.get("matchday"),
            "utc": m.get("utcDate"),
            "status": m.get("status"),
            "result": result,
            "fd_id": m.get("id"),
        })
    return out
