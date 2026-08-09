# EDIT-D · Сценарий: D1 архитектор, D2 прозаик, D3 ToV

**Слой:** D1–D3 (веха 3)
**Вход:** замороженный `Dossier`
**Выход:** `ScriptDraft` с таймкодами (после D3, `tov_applied=true`)
**Блокирует без таймкодов:** E2 (критик удержания)

---

## Зачем

Сценарист не имеет фактов кроме досье (инвариант 1). Структура и проза —
разные вызовы (инвариант 2): D1 планирует секунды, D2 пишет текст, D3 только
полирует речь по словарю персонажа и не добавляет фактов.

Формула тела (как в E7):

`улика → разрыв → причина → доказательство → перенос → кода`

---

## Контракты

См. `models/scenario.py`.

- `BeatRole`: hook_evidence / rupture / cause / proof / transfer / coda
- `BeatList`: обязательные таймкоды без дыр/перекрытий; роли hook+rupture+cause+proof+coda
- `ScriptDraft.lines[*]`: t_start/t_end + claim_id
- `ToneOfVoice`: `config/tov.yaml`

---

## Правила

### D1
- Только frozen dossier.
- `target_duration_sec` из `config/thresholds.yaml` (scenario).
- Hard fail Pydantic, если нет таймкодов / дыры / нет обязательных ролей.

### D2
- Пишет только из досье + BeatList.
- Чужой `claim_id` в line → ValueError.
- Не приветствует и не обещает «в этом видео».

### D3
- Отдельный промпт/вызов.
- Сохраняет число строк, таймкоды и claim_id; меняет wording.
- Словарь — `config/tov.yaml`.

---

## Граф (веха 3)

```
A2 → B2 → C1 → C2 → C3(freeze) → D1 → D2 → D3 → E1 → E2
```

Веха 2 со stub D сохранена как `build_v2_slice_graph`.
