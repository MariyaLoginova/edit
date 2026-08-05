# Источники для A1

Сюда кладётся глава/фрагмент книги — вход сегментации.

- Формат: `.txt` или `.md`, UTF-8.
- Заголовки: строка `Глава N…` или `# Заголовок` — A1 подхватит как `heading`.
- Перевод на A1 не делается: цитаты остаются в языке оригинала; `language` задаётся
  флагом CLI (`--language ru|en`).

## Прогон

```bash
# только сегментация (без API)
python3 scripts/run_a1_a2_matrix.py sources/ВАША-ГЛАВА.txt --a1-only

# полная матрица strategy × model (нужен KIE_API_KEY)
python3 scripts/smoke_kie.py
python3 scripts/run_a1_a2_matrix.py sources/ВАША-ГЛАВА.txt --language en
```

Артефакты: `runs/{source_id}/`. Ручная оценка — в `runs/{source_id}/NOTES.md`.

`sample-little-black-dress.txt` — короткий стенд для офлайн-тестов A1 (не замена
реальной главе владельца).
