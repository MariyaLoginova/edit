# EDIT-A1 · Сегментация источника + первый живой прогон A1→A2

**Слой:** добыча (A1) + первый end-to-end прогон  
**Вход:** книга/глава в `sources/`  
**Выход:** `SourceMap` → живые `ClaimCard` (матрица strategy × model)  
**Зависит от:** веха 0, тикет A2

---

## Зачем

Без A1 майнер A2 нельзя честно прогнать на настоящем тексте. Тикет закрывает
открытый вопрос README про формат `source_map` **прогоном**, не умозрительно, и
подключает KIE как LLM-провайдер.

## A1 — сегментация

Реализация: [`edit/a1_segment.py`](../edit/a1_segment.py). Контракт:
[`models/source.py`](../models/source.py).

| Стратегия | Как режет |
|---|---|
| `paragraph` | по пустым строкам / заголовкам |
| `semantic` | склейка соседних абзацев до `semantic_max_tokens`; смена heading — граница (без эмбеддингов) |
| `fixed_window` | окна по N «токенам» (слова) с overlap |

`token_estimate` ≈ `len/4`. Перевод на A1 не делается; `language` только метка.

Параметры — `config/llm.yaml → segmentation`. Provisional default: `semantic`
(подтвердить/сменить после `runs/*/NOTES.md`).

## KIE

- Ключ: `KIE_API_KEY` в `.env` (см. `.env.example`), не в репо.
- Модели и path_prefix: `config/llm.yaml`.
- Адаптер: [`edit/kie_client.py`](../edit/kie_client.py); узлы зовут
  `edit.llm.get_chat_model`.
- Smoke: `python3 scripts/smoke_kie.py`.
- Невалидный JSON → ретрай (`edit.llm.invoke_json`), без ручной «починки».

## Матрица A1→A2

```bash
python3 scripts/run_a1_a2_matrix.py sources/ГЛАВА.txt --language en
# или только A1:
python3 scripts/run_a1_a2_matrix.py sources/ГЛАВА.txt --a1-only
```

Артефакты: `runs/{source_id}/{strategy}_{model}.json` + `NOTES.md` (ручная оценка).

На что смотреть глазами: причинность, разрыв ожидания, visual_hint, цитата в
сегменте, тишина на биографическом абзаце.

## Критерии приёмки

- [x] A1 режет тремя стратегиями, `SourceMap` валиден.
- [x] `segment_id` / `ordinal` стабильны между прогонами.
- [x] KIE-адаптер + `smoke_kie.py` (зелёный при живом `KIE_API_KEY`).
- [x] Ключ в `.env`; модель в конфиге.
- [ ] ≥6 наборов карточек в `runs/` на реальной главе владельца.
- [ ] Ручная оценка в `runs/*/NOTES.md`.
- [ ] Стратегия по умолчанию зафиксирована по прогону (сейчас provisional: semantic).
- [ ] Автопроверка цитат: `citation_check.rate` в каждом JSON матрицы.

## Замечания

- Не разгонять на всю книгу, пока карточки не подтверждены на одной главе.
- Плохие карточки на всех клетках матрицы — сигнал чинить промпт A2 сейчас.
- CineFlow-репозиторий приватный для этого агента: клиент собран по
  OpenAI-compatible путям docs.kie.ai; при расхождении path_prefix с CineFlow —
  поправить одну строку в `config/llm.yaml`.
