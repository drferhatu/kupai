"""KupAI LLM tahmin motoru: Claude + GPT + Gemini.

Her oynanmamış maç için her modele skor tahmini sordurur ve matches.json'a yazar.
Tahminler artımlı kaydedilir (çökerse kaldığı yerden devam eder, harcamayı tekrarlamaz).
'ferhat' sütunu buradan DOLDURULMAZ — o senin manuel girişin.

Kullanım:
    python src/predict.py --validate     # her modeli 1 çağrıyla test et (toplu harcama yok)
    python src/predict.py                 # tüm eksik tahminleri üret
    python src/predict.py --player claude # sadece bir modeli üret
    python src/predict.py --limit 3       # ilk 3 maçla sınırla (deneme)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "matches.json")

# Her oyuncunun kullandığı model (sağlayıcının güçlü ama ekonomik bir modeli)
MODELS = {
    "claude": "claude-sonnet-4-6",
    "chatgpt": "gpt-4o",
    "gemini": "gemini-2.5-flash",
}

SYSTEM = (
    "Sen bir spor tahmin oyunu için çalışan deneyimli bir futbol analistisin. "
    "Her maç için mutlaka en olası skoru tahmin edersin; tahmin etmeyi asla reddetmezsin. "
    "Yalnızca istenen JSON formatında yanıt verirsin, başka hiçbir şey yazmazsın."
)

PROMPT = (
    "2026 FIFA Dünya Kupası grup aşaması maçı:\n"
    "{home} (ev sahibi) — {away} (deplasman), Grup {group}.\n"
    "Bu maçın en olası skorunu tahmin et. Takımların güncel gücünü dikkate al.\n"
    "SADECE şu JSON ile cevap ver:\n"
    '{{"home": <ev sahibi gol sayısı>, "away": <deplasman gol sayısı>}}'
)


def load_env():
    """.env'deki anahtarları ortam değişkenlerine yükler (zaten varsa dokunmaz)."""
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def parse_score(text: str):
    """Model çıktısından (ev, dep) gol sayısını çıkarır. Bulamazsa None."""
    if not text:
        return None
    # Önce JSON dene
    m = re.search(r'\{[^{}]*"home"\s*:\s*(\d+)[^{}]*"away"\s*:\s*(\d+)[^{}]*\}', text)
    if m:
        return int(m.group(1)), int(m.group(2))
    # Yedek: "2-1" gibi bir kalıp
    m = re.search(r'(\d+)\s*[-:]\s*(\d+)', text)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None


# --- Sağlayıcı çağrıları ---

def call_claude(prompt: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=MODELS["claude"], max_tokens=80, temperature=0.3, system=SYSTEM,
        messages=[{"role": "user", "content": prompt}])
    return msg.content[0].text


def call_chatgpt(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model=MODELS["chatgpt"], max_tokens=80, temperature=0.3,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": prompt}])
    return resp.choices[0].message.content


def call_gemini(prompt: str) -> str:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=MODELS["gemini"], contents=prompt,
        config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.3))
    return resp.text


CALLERS = {"claude": call_claude, "chatgpt": call_chatgpt, "gemini": call_gemini}


def predict_once(player: str, home: str, away: str, group: str, retries: int = 2):
    """Tek tahmin; birkaç kez yeniden dener. (ev, dep) ya da None.

    429/rate-limit hatasında uzun (≈25sn) bekler; diğer hatalarda kısa backoff.
    """
    prompt = PROMPT.format(home=home, away=away, group=group)
    for attempt in range(1, retries + 1):
        try:
            text = CALLERS[player](prompt)
            score = parse_score(text)
            if score:
                return score
            print(f"    ! {player}: ayrıştırılamadı: {text!r}")
        except Exception as e:
            msg = str(e)
            rate = "429" in msg or "RESOURCE_EXHAUSTED" in msg or "rate" in msg.lower()
            print(f"    ! {player} hata (deneme {attempt}/{retries}): "
                  f"{type(e).__name__}: {msg[:120]}")
            if attempt < retries:
                time.sleep(25 if rate else 2 * attempt)
    return None


def validate():
    """Her modeli tek bir örnek maçla test eder — toplu harcamadan önce güvenlik kontrolü."""
    print("Doğrulama: her model için tek örnek tahmin (Türkiye — ABD, Grup D)\n")
    ok = True
    for player in ("claude", "chatgpt", "gemini"):
        print(f"  {player} ({MODELS[player]}):")
        score = predict_once(player, "Türkiye", "ABD", "D")
        if score:
            print(f"    ✓ tahmin: {score[0]}-{score[1]}")
        else:
            print("    ✗ BAŞARISIZ")
            ok = False
    print("\n" + ("✅ Üç model de hazır — tam çalıştırmaya geçebiliriz." if ok
                   else "⚠ En az bir model başarısız — düzeltmeden tam çalıştırma yapma."))
    return ok


def run(players, limit=None, delay=0.4, retries=2):
    load_env()
    with open(DATA, encoding="utf-8") as f:
        data = json.load(f)
    data["models"] = dict(MODELS)  # şeffaflık: hangi model kullanıldı

    targets = [m for m in data["matches"] if m["status"] == "scheduled"]
    if limit:
        targets = targets[:limit]

    todo = sum(1 for m in targets for p in players if not m["predictions"].get(p))
    print(f"{len(targets)} oynanmamış maç, {todo} eksik tahmin üretilecek "
          f"({', '.join(players)}).\n")

    done = fail = 0
    for m in targets:
        for p in players:
            if m["predictions"].get(p):  # zaten var -> atla (resume)
                continue
            score = predict_once(p, m["home"], m["away"], m["group"], retries=retries)
            if score:
                m["predictions"][p] = {"home": score[0], "away": score[1]}
                done += 1
                print(f"  {m['home']} - {m['away']} [{p}]: {score[0]}-{score[1]}")
            else:
                fail += 1
            # Her çağrıdan sonra kaydet (artımlı, resume güvenli)
            with open(DATA, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            time.sleep(delay)  # sağlayıcılara nazik ol

    print(f"\nBitti: {done} tahmin yazıldı, {fail} başarısız.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--player", choices=list(CALLERS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--delay", type=float, default=0.4, help="çağrılar arası bekleme (sn)")
    ap.add_argument("--retries", type=int, default=2, help="çağrı başına deneme sayısı")
    args = ap.parse_args()

    load_env()
    if args.validate:
        sys.exit(0 if validate() else 1)
    players = [args.player] if args.player else ["claude", "chatgpt", "gemini"]
    run(players, limit=args.limit, delay=args.delay, retries=args.retries)


if __name__ == "__main__":
    main()
