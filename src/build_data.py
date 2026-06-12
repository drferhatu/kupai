"""2026 Dünya Kupası grup aşaması fikstürünü matches.json olarak üretir.

Eşleşmeler aicup.replit.app'ten alındı (tam round-robin, 12 grup x 6 maç = 72).
Takım adları Türkçe gösterilir; API eşleştirmesi için İngilizce ad da saklanır.
Maç tarihleri (kickoff) sonradan fixtures.py ile football-data.org'dan doldurulur.

Tahminler (chatgpt/claude/gemini/ferhat) başta boştur; predict.py ile üretilecek.
Sadece oynanmış maçların 'result' alanı doludur.
"""

from __future__ import annotations

import json
import os

# İngilizce -> Türkçe gösterim adı
TR = {
    "Mexico": "Meksika", "South Africa": "Güney Afrika", "Korea Republic": "Güney Kore",
    "Czechia": "Çekya", "Canada": "Kanada", "Bosnia and Herzegovina": "Bosna-Hersek",
    "Qatar": "Katar", "Switzerland": "İsviçre", "Brazil": "Brezilya", "Morocco": "Fas",
    "Haiti": "Haiti", "Scotland": "İskoçya", "USA": "ABD", "Paraguay": "Paraguay",
    "Australia": "Avustralya", "Türkiye": "Türkiye", "Germany": "Almanya",
    "Curaçao": "Curaçao", "Côte d'Ivoire": "Fildişi Sahili", "Ecuador": "Ekvador",
    "Netherlands": "Hollanda", "Japan": "Japonya", "Sweden": "İsveç", "Tunisia": "Tunus",
    "Belgium": "Belçika", "Egypt": "Mısır", "IR Iran": "İran", "New Zealand": "Yeni Zelanda",
    "Spain": "İspanya", "Cabo Verde": "Yeşil Burun", "Saudi Arabia": "Suudi Arabistan",
    "Uruguay": "Uruguay", "France": "Fransa", "Senegal": "Senegal", "Iraq": "Irak",
    "Norway": "Norveç", "Argentina": "Arjantin", "Algeria": "Cezayir", "Austria": "Avusturya",
    "Jordan": "Ürdün", "Portugal": "Portekiz", "DR Congo": "DR Kongo",
    "Uzbekistan": "Özbekistan", "Colombia": "Kolombiya", "England": "İngiltere",
    "Croatia": "Hırvatistan", "Ghana": "Gana", "Panama": "Panama",
}

# Her grup için 3 maç günü; her maç günü 2 eşleşme: (ev, deplasman)
# Sıralama referans sitedeki kronolojik blok düzenidir.
GROUPS = {
    "A": [[("Mexico", "South Africa"), ("Korea Republic", "Czechia")],
          [("Czechia", "South Africa"), ("Mexico", "Korea Republic")],
          [("Czechia", "Mexico"), ("South Africa", "Korea Republic")]],
    "B": [[("Canada", "Bosnia and Herzegovina"), ("Qatar", "Switzerland")],
          [("Switzerland", "Bosnia and Herzegovina"), ("Canada", "Qatar")],
          [("Switzerland", "Canada"), ("Bosnia and Herzegovina", "Qatar")]],
    "C": [[("Brazil", "Morocco"), ("Haiti", "Scotland")],
          [("Scotland", "Morocco"), ("Brazil", "Haiti")],
          [("Scotland", "Brazil"), ("Morocco", "Haiti")]],
    "D": [[("USA", "Paraguay"), ("Australia", "Türkiye")],
          [("USA", "Australia"), ("Türkiye", "Paraguay")],
          [("Türkiye", "USA"), ("Paraguay", "Australia")]],
    "E": [[("Germany", "Curaçao"), ("Côte d'Ivoire", "Ecuador")],
          [("Germany", "Côte d'Ivoire"), ("Ecuador", "Curaçao")],
          [("Curaçao", "Côte d'Ivoire"), ("Ecuador", "Germany")]],
    "F": [[("Netherlands", "Japan"), ("Sweden", "Tunisia")],
          [("Netherlands", "Sweden"), ("Tunisia", "Japan")],
          [("Japan", "Sweden"), ("Tunisia", "Netherlands")]],
    "G": [[("Belgium", "Egypt"), ("IR Iran", "New Zealand")],
          [("Belgium", "IR Iran"), ("New Zealand", "Egypt")],
          [("Egypt", "IR Iran"), ("New Zealand", "Belgium")]],
    "H": [[("Spain", "Cabo Verde"), ("Saudi Arabia", "Uruguay")],
          [("Spain", "Saudi Arabia"), ("Uruguay", "Cabo Verde")],
          [("Cabo Verde", "Saudi Arabia"), ("Uruguay", "Spain")]],
    "I": [[("France", "Senegal"), ("Iraq", "Norway")],
          [("France", "Iraq"), ("Norway", "Senegal")],
          [("Norway", "France"), ("Senegal", "Iraq")]],
    "J": [[("Argentina", "Algeria"), ("Austria", "Jordan")],
          [("Argentina", "Austria"), ("Jordan", "Algeria")],
          [("Algeria", "Austria"), ("Jordan", "Argentina")]],
    "K": [[("Portugal", "DR Congo"), ("Uzbekistan", "Colombia")],
          [("Portugal", "Uzbekistan"), ("Colombia", "DR Congo")],
          [("Colombia", "Portugal"), ("DR Congo", "Uzbekistan")]],
    "L": [[("England", "Croatia"), ("Ghana", "Panama")],
          [("England", "Ghana"), ("Panama", "Croatia")],
          [("Panama", "England"), ("Croatia", "Ghana")]],
}

# Oynanmış maçların sonuçları: (grup, ev_en, dep_en) -> (ev_gol, dep_gol)
RESULTS = {
    ("A", "Mexico", "South Africa"): (2, 0),
    ("A", "Korea Republic", "Czechia"): (2, 1),
}

PLAYERS = ["chatgpt", "claude", "gemini", "ferhat"]


def build() -> dict:
    matches = []
    for group, matchdays in GROUPS.items():
        for md_idx, pairings in enumerate(matchdays, start=1):
            for slot, (home_en, away_en) in enumerate(pairings, start=1):
                mid = f"{group}-MD{md_idx}-{slot}"
                result = RESULTS.get((group, home_en, away_en))
                matches.append({
                    "id": mid,
                    "group": group,
                    "matchday": md_idx,
                    "home": TR[home_en], "away": TR[away_en],
                    "home_en": home_en, "away_en": away_en,
                    "kickoff": None,  # fixtures.py dolduracak
                    "status": "finished" if result else "scheduled",
                    "result": ({"home": result[0], "away": result[1]} if result else None),
                    "predictions": {p: None for p in PLAYERS},
                })
    return {
        "tournament": "FIFA Dünya Kupası 2026",
        "players": PLAYERS,
        "matches": matches,
    }


if __name__ == "__main__":
    data = build()
    out = os.path.join(os.path.dirname(__file__), "..", "data", "matches.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    n = len(data["matches"])
    played = sum(1 for m in data["matches"] if m["status"] == "finished")
    print(f"matches.json yazıldı: {n} maç ({played} oynanmış, {n - played} bekliyor)")
