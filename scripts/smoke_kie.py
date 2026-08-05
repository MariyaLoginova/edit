#!/usr/bin/env python3
"""Smoke-тест KIE: на каждой модели из config/llm.yaml — JSON {ok: true}."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from edit.kie_client import kie_api_key, list_configured_models, load_llm_config
from edit.llm import get_chat_model, invoke_json


def main() -> int:
    load_llm_config()
    try:
        kie_api_key()
    except RuntimeError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2

    models = list_configured_models()
    if not models:
        print("FAIL: нет models в config/llm.yaml", file=sys.stderr)
        return 2

    failed = 0
    for model_id in models:
        print(f"→ {model_id} …", flush=True)
        try:
            llm = get_chat_model(model=model_id, temperature=0.0)
            data = invoke_json(
                llm,
                [
                    {
                        "role": "system",
                        "content": "Отвечай только валидным JSON без markdown.",
                    },
                    {
                        "role": "user",
                        "content": 'Верни ровно JSON-объект {"ok": true}',
                    },
                ],
                retries=1,
            )
            if not isinstance(data, dict) or data.get("ok") is not True:
                raise ValueError(f"неожиданный ответ: {data!r}")
            print(f"  OK {model_id}: {json.dumps(data, ensure_ascii=False)}")
        except Exception as exc:  # noqa: BLE001 — smoke печатает любую ошибку модели
            failed += 1
            print(f"  FAIL {model_id}: {exc}", file=sys.stderr)

    if failed:
        print(f"Итого: {failed}/{len(models)} моделей упали", file=sys.stderr)
        return 1
    print(f"Итого: все {len(models)} моделей ответили валидным JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
