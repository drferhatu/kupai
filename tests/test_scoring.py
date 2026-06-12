"""scoring.py için birim testleri.

Doğrulama referansı olarak aicup.replit.app'teki oynanmış 2 maçı kullanıyoruz;
motorumuz o sitedeki puanları birebir üretmeli.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from scoring import outcome, score_prediction  # noqa: E402


def test_outcome():
    assert outcome(2, 0) == "H"
    assert outcome(0, 2) == "A"
    assert outcome(1, 1) == "D"


def test_exact_score():
    assert score_prediction(2, 0, 2, 0) == 3
    assert score_prediction(0, 0, 0, 0) == 3  # tam beraberlik


def test_correct_goal_difference():
    # Ev kazandı, gol farkı +2 == +2 ama skor farklı
    assert score_prediction(2, 0, 3, 1) == 2
    # Doğru ama tam olmayan beraberlik: gf 0 == 0
    assert score_prediction(1, 1, 2, 2) == 2


def test_correct_winner_only():
    # Ev kazandı ama gol farkı tutmadı (+2 vs +1)
    assert score_prediction(2, 0, 1, 0) == 1
    assert score_prediction(5, 1, 2, 0) == 1


def test_wrong_winner():
    assert score_prediction(1, 1, 2, 1) == 0  # beraberlik dedi, ev kazandı
    assert score_prediction(2, 0, 0, 1) == 0  # ev dedi, deplasman kazandı


# --- Referans site doğrulaması (oynanmış 2 maç) ---

def test_reference_mexico_south_africa():
    # Gerçek: Meksika 2-0
    a_h, a_a = 2, 0
    assert score_prediction(2, 0, a_h, a_a) == 3  # ChatGPT 2-0
    assert score_prediction(2, 0, a_h, a_a) == 3  # Claude 2-0
    assert score_prediction(5, 1, a_h, a_a) == 1  # Gemini 5-1
    assert score_prediction(3, 0, a_h, a_a) == 1  # Fawzi 3-0


def test_reference_korea_czechia():
    # Gerçek: Güney Kore 2-1 ; herkes beraberlik demişti -> 0
    a_h, a_a = 2, 1
    assert score_prediction(1, 1, a_h, a_a) == 0
    assert score_prediction(0, 0, a_h, a_a) == 0
