# EDIT-F1 + G1 · Раскадровка и петля обучения (веха 5)

**F1 вход:** `ScriptDraft` + frozen `Dossier`  
**F1 выход:** `ShotList` (пачка картинок на фразу)  
**G1 вход:** `list[RolloutMetrics]`  
**G1 выход:** `WeightUpdate` → веса B1 / порог E2 в `config/thresholds.yaml`

---

## F1 · Раскадровка

На каждую фразу сценария — веб-поиск картинок (тот же soft_match, что C2).
Отбор слоёв и права — **вручную на монтаже**, вне графа (ADR-002).

Контракт: `models/shots.py` (`ShotPacket.images[]`).

## B1 · Скоринг (чтобы G1 было куда писать)

5 осей: `surprise`, `visuality`, `causal_clarity`, `evidence`, `shareability`.
Веса — `config/thresholds.yaml → scoring.weights`. Эвристики дешёвые, без LLM.

## G1 · Пост-аналитик

По метрикам досмотра / отвала 0–3с / шеров / сохранений сдвигает веса и
иногда предлагает ужесточить `dropoff_score_threshold`.

Пока `n < learning.min_rollouts_for_calibration` (15) — `hypothesis=true`:
вердикты E2 читать как список подозрений.

G1 живёт в отдельном графе `build_learning_graph` (offline после выпуска).

---

## Граф вехи 5

```
A2 → B1 → B2 → C → D → E1…E6 → gate → F1
                                      ↘ blocked
```

F2 (вычитка вслух) — человек, вне графа. E7 — отдельный человеческий гейт.

---

## Критерии приёмки

- [x] F1 даёт ≥1 shot на каждую line сценария; soft_match проставляется.
- [x] B1 ранжирует список ClaimCard по weighted total.
- [x] G1 при высоком dropoff_3s поднимает surprise/visuality.
- [x] G1 при n<15 ставит hypothesis=true.
- [x] Тесты без сети (FakeSearcher).
