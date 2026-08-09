# Аудит последнего прогона · GLM-5.2 · `lilli-glm-full`

**Когда:** 2026-08-07 ~10:00–10:04 UTC  
**Модель:** `glm-5.2` (AIHubMix)  
**Скрипт:** `scripts/run_lilli_glm_full.py`  
**Цепочка:** claim+глава → E-editor → C1 (local search) → C1.5 research enricher → freeze → D2 monologue → E-check

> В этом прогоне wrapper `AuditedLLM` не писался: сохранены входы/выходы узлов и один сырой ответ E-editor (ранний). Ниже — полная реконструкция по артефактам.

---

## 0. Вход

**Claim** (`00_claim.json`):
- id: `barbie-lilli-steal-like-artist`
- claim: «Первая Барби в полосатом купальнике почти копирует немецкую Лилли: фигуру оставили, соски убрали — и взрослую новинку выпустили как подростковую модель.»
- counter: «Барби придумали с нуля как идеальный образ американской девочки-подростка.»
- mechanism: `кража-с-переносом`

**Источник** (`00_source_block.txt`): выдержка гл.3 Горалик «Полая женщина» (~17 KB), Барби ← Лилли.

---

## 1. E-editor · LLM #1

**System** (`edit/prompts/e_editor.txt`):
```
Ты — редактор личного канала Марии. Тебе дали полный первичный текст книги и
аудиторию. Найди в нём сильную главную мысль...
Верни JSON StoryBrief.
```

**User payload:** `{claim, primary_text, audience, menu_story_methods, hook_triggers}`

**Получено → нормализовано** (`01_story_brief.json`):
| поле | значение |
|---|---|
| main_thought | Знаменитые «неправильные» пропорции Барби — … Рут Хендлер взяла готовую куклу Лилли из немецкого секс-шопа… (обрезано до 400) |
| recommended_method | `a_vot_nifiga` |
| alternatives | `bylo_stalo`, `lozhnyy_sled` |
| opening | Барби придумали с нуля как идеальный образ американской девочки-подростка. |
| research_queries | 4 запроса (Bild Lilli / Ruth Handler+Jack Ryan / Anthony Boulon / 1950s comic silhouette) |
| proof_plan | `[]` |
| ending_type | `formula` |

Ранний сырой ответ (другой прогон ~09:57) лежит в `00_eeditor_raw_response.txt` — не совпадает с финальным brief; финальный brief от прогона 10:00.

---

## 2. C1 material · без LLM

`PrimarySourceSearcher` (нет `BRAVE_API_KEY`): на каждый `research_query` вернул один hit:
- url: `local://goralik-polaya-zhenshchina/ch03`
- snippet: весь первичный текст

→ 4 web_confirmations, все на local primary.

---

## 3. C1.5 research enricher · LLM #2

**System** (`edit/prompts/c1_research_enricher.txt`): отобрать доп. факты с URL; если поиска нет — пустой `facts` + `gaps`.

**User payload:** `{claim_id, primary_text/material_notes, story_brief, web_results×4 local}`

**Получено** (`02_research_pack.json`):
- `facts`: `[]` — внешних URL нет, факты не добавлены
- `gaps`: 8 пунктов (дата релиза Барби, Bild Lilli/Beuthien, Jack Ryan, Boulon, стиль комиксов 50-х, Mattel vs Greiner & Hausser, Bud Westmore…)
- `summary`: «Исследователь не дал резюме.»

Dossier frozen @ `2026-08-07T10:01:37Z` (`03_dossier.json`).

---

## 4. D2 monologue · LLM #3

**System** (`edit/prompts/d2_monologue.txt`): Мария, арт-директор; 150–300 слов; proof_plan + story method; финал formula/question.

**User payload:** `{dossier.claim, material_notes, web_confirmations, audience, story_brief, story_method=a_vot_nifiga, word_limit 150–300}`

**Получено** (`04_monologue.json`) — **это актуальный монолог последнего прогона**:

```
Все думают, что Барби — чистый американский дизайн с нуля. Идеальная девочка-подросток, teen fashion model, мечта. А вот нифига.

Читаю у Горалик — и отвисает. Рут Хендлер привезла из Европы куклу. Из секс-шопа. Лилли — трёхмерная версия комикса из Bild Zeitung, проститутка с характером, наглая хищница. Мужики покупали её в магазинах для взрослых, таскали в кармане, вешали на лобовое стекло. Сисястая кукла в микро-купальнике.

И Хендлер говорит дизайнерам: «Сделайте из Лилли тинэйджера». Всё. Вот весь бриф.

Что сделали? Фигуру оставили как есть. Тонкая талия, крутая попа, треугольная голова — это же комиксный стиль «дамочек» 50-х, карикатура, пародия. Соски убрали. Макияж чуть пристойнее. Завиток на лоб сменили кудрявой чёлкой. Купальник тот же, пропорции те же, шпильки, цыганские серьги, голубые тени, алая помада.

Первыми рецензентам кукла казалась «пугающей, порочной и открыто предлагающей себя». Они даже не знали про Лилли — просто видели результат. Потому что это и была не девочка-подросток. Это была проститутка из немецкого таблоида, которой стёрли соски и повесили ярлык «teenage fashion model».

Вот это и есть кража-с-переносом: берёшь готовый силуэт, меняешь контекст — и карикатура на шлюшку становится иконой невинности.

Сколько визуальных икон вокруг нас — тоже просто украденные силуэты с другим ценником?
```

- words: **194**
- method: `a_vot_nifiga`
- ending: `formula` (+ вопрос в конце)

---

## 5. E-check · LLM #4

**System** (`edit/prompts/e_check.txt`): сверка с primary + web; плотность ≥3 деталей; JSON MonologueCheck.

**User payload:** `{monologue, source_material, source_citation, web_confirmations}`

**Получено** (`05_echeck.json`):
- `passes`: **true**
- `factual_issues`: `[]`
- `overclaim_issues`: `[]`
- `summary`: «Монолог добросовестно следует источнику… Ключевые факты … подтверждены первичным текстом. Найдены minor imprecisions и один overclaim формулировки.»  
  *(в issues пусто — модель написала оговорку в summary, но severity≥4 не выставила)*

---

## Итог по вызовам

| # | этап | LLM? | артефакт | статус |
|---|---|---|---|---|
| 0 | вход claim+глава | нет | `00_*` | ok |
| 1 | E-editor | glm-5.2 | `01_story_brief.json` | ok → method `a_vot_nifiga`, 4 queries |
| 2 | C1 search | нет (local stub) | в `03_dossier` | ok, без Brave |
| 3 | C1.5 enricher | glm-5.2 | `02_research_pack.json` | ok, facts=[], gaps×8 |
| 4 | D2 monologue | glm-5.2 | `04_monologue.json` | ok, 194 слова |
| 5 | E-check | glm-5.2 | `05_echeck.json` | passes=true |

**Всего LLM-вызовов в успешном прогоне: 4** (E-editor, C1.5, D2, E-check).
