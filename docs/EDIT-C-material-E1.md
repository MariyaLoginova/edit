# EDIT-C + E1 · Материал, мягкий фактчек, заморозка досье, трассируемость

**Слой:** C1–C3 + E1 (веха 2)
**Статус:** реализовано по ADR-002 / EDIT-00 (отдельного исходного тикета не было)
**Вход C:** выбранный `ClaimCard` (после B2)
**Выход C:** замороженный `Dossier` (SSOT)
**Вход E1:** `ScriptDraft` + frozen `Dossier`
**Выход E1:** `TraceReport` (`passes=false` → блокер до F)

---

## Зачем

После отбора темы система должна собрать материал и **запретить сценаристу
дописывать факты**. ADR-002 снимает SAFE/права/архивы, но оставляет:

1. лёгкое веб-подтверждение тезиса (C1);
2. пачку картинок из поиска без отбора прав в графе (C2);
3. одну LLM-развилку «не выдумано ли» по датам/именам/атрибуциям (C3);
4. заморозку досье перед D;
5. структурный аудит трассируемости фактов в сценарии (E1).

---

## Контракты

См. `models/dossier.py`, `models/trace.py`.

- `WebConfirmation` — url/title/snippet + мягкий `supports_claim`
- `ImageCandidate` — url + `soft_match` (метаданные ≈ запрос)
- `SoftFactcheckResult` — `{ok, invented_items, rationale}`
- `Dossier.freeze()` — только при `soft_factcheck.ok`; дальше `ensure_mutable()` бросает
- `TraceReport` — hard fail на `missing_claim_id` / `unknown_claim_id` / unfrozen dossier

**Нет полей лицензий/правового статуса** — сознательно (ADR-002).

---

## Правила узлов

### C1
- Запрос = claim + scope; поиск через injectable `WebSearcher` (Brave при
  `BRAVE_API_KEY`, иначе пусто / Fake в тестах).
- Опционально LLM сжимает сниппеты в `material_notes` и проставляет
  `supports_claim`. Фактчекер-сценарий не вызывается.

### C2
- Запрос = `visual_hint` (+ author_or_work).
- Критерий годности: пересечение токенов query ∩ (title+description).
- Пачка кладётся в `image_candidates`; человек отбирает на монтаже.

### C3
- Отдельный вызов. **Не видит сценарий** (инвариант 2).
- При `ok=true` — `dossier.freeze()`; при `ok=false` — досье не замораживается,
  граф уходит в blocked.

### E1
- Требует `dossier.frozen`.
- Каждая фактическая реплика → `claim_id` из досье.
- `claim_id=None` допускается только для маркеров мнения/коротких связок.
- Не переписывает текст — только вердикт.

---

## Граф (веха 2)

```
A2 → B2-stub → C1 → C2 → C3(+freeze) → D-stub(manual script) → E1 → E2
```

D по-прежнему ручной до вехи 3.

---

## Критерии приёмки

- [x] C3 fail → `frozen=false`, прод блокируется.
- [x] После freeze мутация досье → RuntimeError.
- [x] E1 fail на реплике без `claim_id` и на чужом `claim_id`.
- [x] E1 fail, если досье не заморожено.
- [x] C2 помечает `soft_match` по метаданным, не CV.
- [x] Юнит-тесты на FakeLLM / FakeSearcher без сети.
