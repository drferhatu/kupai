"""Ferhat'ın tahminlerini stratejiyle üretir (predictions['ferhat']).

Strateji ("Ferhat personası"):
  1. Türkiye'nin oynadığı maçta Türkiye kazanır.
  2. Diğer maçlarda AI konsensüsünün favorisini tutar, ama daha cesur/net skorla.
  3. Skor, üç AI'nın (claude/chatgpt/gemini) hiçbiriyle BİREBİR aynı olamaz.

Çağrı yok, harcama yok — saf strateji. AI tahminleri tamamlandıktan sonra çalıştır:
    python src/ferhat.py
"""

from __future__ import annotations

import json
import os
from collections import Counter

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "matches.json")
TURKIYE = "Türkiye"
AI = ("claude", "chatgpt", "gemini")

# Galip perspektifinden, "cesur" sıraya göre skor adayları (galip-mağlup).
WIN_CANDS = [(2, 1), (3, 1), (2, 0), (3, 0), (1, 0), (4, 1), (3, 2), (4, 2), (4, 0)]
DRAW_CANDS = [(2, 2), (1, 1), (3, 3), (0, 0)]


def outcome(h: int, a: int) -> str:
    return "H" if h > a else "A" if a > h else "D"


def consensus(ai_preds: list[dict]) -> str:
    """AI tahminlerinin çoğunluk sonucunu döndürür (H/D/A). Boşsa 'H'."""
    if not ai_preds:
        return "H"
    c = Counter(outcome(p["home"], p["away"]) for p in ai_preds)
    # Tie-break: ev galibiyeti > deplasman > beraberlik
    return max(c, key=lambda k: (c[k], {"H": 2, "A": 1, "D": 0}[k]))


def ferhat_pick(m: dict) -> tuple[int, int]:
    home, away = m["home"], m["away"]
    ai_preds = [m["predictions"][p] for p in AI if m["predictions"].get(p)]
    ai_tuples = {(p["home"], p["away"]) for p in ai_preds}

    # 1) Hedef galip
    if home == TURKIYE:
        winner = "H"
    elif away == TURKIYE:
        winner = "A"
    else:
        winner = consensus(ai_preds)

    # 2) Galip perspektifini ev/deplasman skoruna çevir
    if winner == "D":
        cands = DRAW_CANDS
    else:
        cands = [(w, l) if winner == "H" else (l, w) for (w, l) in WIN_CANDS]

    # 3) AI'larla çakışmayan ilk cesur skoru seç
    for c in cands:
        if c not in ai_tuples:
            return c
    # Yedek: galibin golünü artırarak benzersizleştir
    h, a = cands[0]
    while (h, a) in ai_tuples:
        if winner == "A":
            a += 1
        else:
            h += 1
    return (h, a)


def run():
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)

    n = 0
    for m in data["matches"]:
        if m["status"] != "scheduled":
            continue
        # Üç AI da dolmadan Ferhat'ı üretme (benzersizlik tam olsun)
        if not all(m["predictions"].get(p) for p in AI):
            continue
        h, a = ferhat_pick(m)
        m["predictions"]["ferhat"] = {"home": h, "away": a}
        n += 1

    with open(DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Ferhat tahminleri üretildi: {n} maç.")
    skipped = sum(1 for m in data["matches"]
                  if m["status"] == "scheduled" and not all(m["predictions"].get(p) for p in AI))
    if skipped:
        print(f"  ⚠ {skipped} maç atlandı (AI tahminleri eksik — Gemini tamamlanınca tekrar çalıştır).")


if __name__ == "__main__":
    run()
