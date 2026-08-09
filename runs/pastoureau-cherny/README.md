# Прогон · Мишель Пастуро · «Черный. История цвета»

Источник: `sources/pastoureau-cherny.txt` (OCR, очищенный).

## Этапы

1. **A2 whole-book → B1** — `scripts/mine_pastoureau_black.py`  
   Книга (~110k tok) уходит **одним** A2-вызовом → shortlist 12–20 тем → B1.  
   Артефакты: `book-a2/book-claims.json`, `scored-topics.json`, `THEME_SHORTLIST.md`  
   (`--by-chapter` — старый дорогой режим, не нужен при длинном контексте)
2. **E → C → D → E-check** — `scripts/run_pastoureau_top.py`  
   Артефакты: `produce-<topic_id>/`

## Команды

```bash
python scripts/mine_pastoureau_black.py --model gpt-5-2
python scripts/run_pastoureau_top.py --model gpt-5-2
```
