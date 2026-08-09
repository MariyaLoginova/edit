# Прогон · Мишель Пастуро · «Черный. История цвета»

Источник: `sources/pastoureau-cherny.txt` (OCR, очищенный).

## Этапы

1. **A2+B1 whole-book** — `scripts/mine_pastoureau_black.py`  
   Книга (~90k tok) → **ровно один** LLM-вызов: темы + оценка привлекательности.  
   Артефакты: `book-a2/book-claims.json`, `scored-topics.json`, `THEME_SHORTLIST.md`
2. **E → C → D → E-check** — только после явного выбора темы / согласия.  
   `scripts/run_pastoureau_top.py`

См. корневой [`AGENTS.md`](../../AGENTS.md): без согласия — никаких массовых
батчей и вторых проходов.

## Команды

```bash
python scripts/mine_pastoureau_black.py --model gemini-2.5-flash
# дальше — только с согласия:
# python scripts/run_pastoureau_top.py --model gpt-5-2
```
