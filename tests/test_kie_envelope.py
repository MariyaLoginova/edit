from __future__ import annotations

import pytest

from edit.kie_client import KieAPIError, _raise_if_kie_envelope
from edit.llm import _is_transient_llm_error


def test_kie_daily_limit_is_not_retryable():
    with pytest.raises(KieAPIError) as exc:
        _raise_if_kie_envelope(
            {
                "code": 433,
                "msg": "The current number of points used by apiKey has exceeded the daily limit",
                "data": None,
            }
        )
    assert exc.value.retryable is False
    assert _is_transient_llm_error(exc.value) is False


def test_openai_shaped_payload_passes():
    _raise_if_kie_envelope({"choices": [{"message": {"content": "ok"}}]})
