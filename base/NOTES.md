# Заметки по базе content-writer (веха 0)

Источник: [`langchain-ai/content-writer`](https://github.com/langchain-ai/content-writer),
каталог `py/`, скопирован в `base/content-writer/` **без изменений кода**.

## Что есть в Python-бэкенде

Весь агент — один файл `content_writer/__init__.py`:

| Элемент | Как устроено |
|---|---|
| State | `GraphState(MessagesState)` + `info: Annotated[dict, SharedValue.on("assistant_id")]` + `userAcceptedText: bool` |
| Узлы | `callModel` (генерация текста по правилам) → `generateInsights` (рефлексия → новые rules) |
| Ветвление | с `START` условное ребро по `userAcceptedText` |
| SharedValue | правила стиля живут вне треда, ключ — `assistant_id` |
| Модели | OpenAI (`gpt-4o-mini`) для письма, Anthropic (`claude-3-5-sonnet`) для рефлексии |

Точка входа LangGraph: `build_graph()` → `workflow.compile()`, прописана в
`langgraph.json` как граф `agent`.

## Что берём для EDIT

По ADR-002 — **паттерн**, не весь продукт:

1. **Типизированный LangGraph state** + условные рёбра / interrupt для HITL.
2. **Изоляция ролей** через разные системные промпты (аналог «ассистентов» с
   разным контекстом) — у нас это отдельные узлы A2 / D2 / E2 / E3 / E7.
3. **SharedValue** — опционально для долгоживущих настроек (ToV, веса B1), не
   для артефактов пайплайна. Артефакты (`ClaimCard`, `Dossier`, …) ходят
   обычными полями state и валидируются Pydantic.

Не тащим: UI на Next.js, Vercel KV под system rules, цикл «REVISION →
переписать rules». EDIT — многоузловой редакционный граф, не персональный
писательский ассистент.

## Как прогнать базу как есть

```bash
cd base/content-writer
cp .env.example .env   # OPENAI_API_KEY, ANTHROPIC_API_KEY
# через LangGraph Studio / `langgraph dev`, граф = agent
# либо: poetry install && python -c "from content_writer import build_graph; g = build_graph(); print(g)"
```

Прогон writing-агента на реальных ключах — ручной шаг владельца; в CI без
ключей достаточно импорта и сборки графа (`tests/test_base_content_writer.py`).

**Совместимость:** апстрим `pyproject.toml` пишет `python <3.12`, но на 3.12
граф собирается. Важно держать **langgraph 0.2.x** — в 1.x модуль
`langgraph.managed.shared_value` удалён, база не импортируется.
