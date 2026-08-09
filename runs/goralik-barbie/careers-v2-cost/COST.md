# Cost · barbie-career-costume-permission

**Всего:** `$0.3935` · 10 LLM calls · 250182 tokens (in 246228 / out 3954)

Прайс: `config/pricing.yaml`

| stage | calls | input | output | USD |
|---|---:|---:|---:|---:|
| E-editor | 1 | 16385 | 1333 | $0.0473 |
| E-hook | 1 | 2994 | 1291 | $0.0233 |
| D2 monologue | 7 | 205031 | 1307 | $0.3162 |
| E-check | 1 | 21818 | 23 | $0.0066 |

## Чистый путь (оценка)

После фикса truncated payload D2 один успешный сценарий roughly:

| stage | model | USD |
|---|---|---:|
| E-editor | gpt-5-2 | $0.0473 |
| E-hook | gpt-5-2 | $0.0233 |
| D2 (1 call, slim) | gemini-3-6-flash | ~$0.0024 |
| E-check | gemini-3-6-flash | $0.0066 |
| **Итого clean** | | **~$0.08** |

Фактический прогон дороже (`$0.3935`), потому что первые D2-попытки слали всю главу (~85k chars) в gpt-5-2 и ловили `message too long`.
Payload теперь обрезан в `edit/d2_monologue.py` / `edit/e_check.py`.
