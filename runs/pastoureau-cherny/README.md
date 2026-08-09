# Прогон · Мишель Пастуро · «Черный. История цвета»

Источник: `sources/pastoureau-cherny.txt` (OCR, очищенный).

## Этапы

1. **A1 → A2 → B1** — `scripts/mine_pastoureau_black.py`  
   Артефакты: `book-a2/ch*.json`, `book-a2/scored-topics.json`, `THEME_SHORTLIST.md`
2. **E → C → D → E-check** — `scripts/run_personal_full_audit.py` по top-теме  
   Артефакты: `produce-<topic_id>/`

## Команды

```bash
python scripts/mine_pastoureau_black.py --model gpt-5-2
python scripts/run_pastoureau_top.py --model gpt-5-2
```
