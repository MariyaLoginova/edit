# Сценарии после FIX-1/2/3

Прогон: `scripts/run_fix_scenario.py` · модель `gpt-5-2`  
Карточки из `../fix1_a2_narrow.json`.

Поиск картинок — **заглушка** (`QueryEchoSearcher`): не курация, а описательные
кандидаты под `contrast_pair`, чтобы dossier gate пропустил freeze и D/F1
собрали VO + примерные кадры. Реальный Brave/архив — отдельный шаг монтажа.

| claim_id | объект | механизм | файл |
|---|---|---|---|
| `cats-crowd-predator-threshold` | котики перед человеком | порог-количества | [SCENARIO.md](cats-crowd-predator-threshold/SCENARIO.md) |
| `cake-candy-face-destruction` | мордочка из конфет | хрупкость-как-таймер | [SCENARIO.md](cake-candy-face-destruction/SCENARIO.md) |
