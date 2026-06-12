# 🏆 KupAI

**KupAI ile Dünya Kupası'nda yapay zekâ modellerine karşı yarışıyorum.**

Her maç için ChatGPT, Claude, Gemini ve Ferhat birer skor tahmini yapar; sistem
gerçek sonuçları otomatik çeker, puanlar ve liderlik tablosunu günceller.

## Puanlama

| Durum | Puan |
|---|---|
| Doğru galip + tam skor | 3 |
| Doğru galip + doğru gol farkı | 2 |
| Doğru galip (sadece) | 1 |
| Yanlış galip | 0 |

## Mimari

Statik site + günlük cron. Dinamik sunucu yok.

```
src/footballdata.py  football-data.org API istemcisi (throttle-aware) + isim eşleme
src/fixtures.py      fikstür + sonuçları çekip data/matches.json'u günceller (günlük cron)
src/build_data.py    grup aşaması fikstürünü ilk kez üretir
src/scoring.py       puanlama motoru (testli)
src/predict.py       LLM tahmin motoru (Claude + GPT + Gemini) — tur başına bir kez
src/build_site.py    matches.json -> site/index.html (açık tema, mobil uyumlu)
data/matches.json    tek veri kaynağı (fikstür, tahminler, sonuçlar)
site/index.html      yayınlanan statik site
```

Günlük güncelleme (`.github/workflows/daily.yml`) yalnızca `fixtures.py` çalıştırır
(tek API çağrısı, LLM harcaması yok), siteyi yeniden kurar ve GitHub Pages'e yayınlar.

## Yerel çalıştırma

```bash
conda activate ferhat_ml
PYTHONPATH=src python src/fixtures.py     # sonuçları çek
PYTHONPATH=src python src/build_site.py   # siteyi kur
python -m http.server -d site 8765        # http://localhost:8765
```

Anahtarlar `.env` dosyasında tutulur (gitignore'da; repoya girmez).

## Test

```bash
PYTHONPATH=src python -c "import sys; sys.path.insert(0,'tests'); import test_scoring as t; [getattr(t,f)() for f in dir(t) if f.startswith('test_')]"
```
