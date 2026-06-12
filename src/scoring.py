"""KupAI puanlama motoru.

Puanlama kuralı (Ferhat'ın tablosu):
    Doğru galip + tam skor          -> 3 puan
    Doğru galip + doğru gol farkı   -> 2 puan
    Doğru galip (sadece)            -> 1 puan
    Yanlış galip                    -> 0 puan

Not: Beraberlik tahmini doğruysa "doğru galip" sayılır. Tam beraberlik
(örn. tahmin 1-1, sonuç 1-1) 3 puan; doğru ama tam olmayan beraberlik
(örn. tahmin 1-1, sonuç 2-2) gol farkı 0=0 olduğundan 2 puandır.
"""

from __future__ import annotations

from typing import Literal

Outcome = Literal["H", "D", "A"]


def outcome(home: int, away: int) -> Outcome:
    """Maçın sonucunu döndürür: H (ev sahibi), D (beraberlik), A (deplasman)."""
    if home > away:
        return "H"
    if home < away:
        return "A"
    return "D"


def score_prediction(
    pred_home: int, pred_away: int, actual_home: int, actual_away: int
) -> int:
    """Tek bir tahmine 0–3 arası puan verir.

    Args:
        pred_home, pred_away: tahmin edilen skor.
        actual_home, actual_away: gerçekleşen skor.

    Returns:
        Kurala göre 0, 1, 2 veya 3 puan.
    """
    # Yanlış galip -> 0
    if outcome(pred_home, pred_away) != outcome(actual_home, actual_away):
        return 0

    # Buradan sonrası: galip/beraberlik doğru bilinmiş.
    # Tam skor -> 3
    if pred_home == actual_home and pred_away == actual_away:
        return 3

    # Doğru gol farkı -> 2  (beraberlikte gol farkı her zaman 0=0)
    if (pred_home - pred_away) == (actual_home - actual_away):
        return 2

    # Sadece doğru galip -> 1
    return 1


def points_label(points: int) -> str:
    """UI rozeti için kısa etiket, örn. '3PT'."""
    return f"{points}PT"


if __name__ == "__main__":  # hızlı elle kontrol
    assert score_prediction(2, 0, 2, 0) == 3  # tam skor
    assert score_prediction(5, 1, 2, 0) == 1  # doğru galip, yanlış skor
    assert score_prediction(1, 1, 2, 1) == 0  # beraberlik dedi, ev kazandı
    print("scoring.py: temel kontroller geçti")
