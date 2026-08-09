from __future__ import annotations

from types import SimpleNamespace

from edit.costing import cost_usd, extract_usage, summarize_calls


def test_extract_usage_from_usage_metadata():
    response = SimpleNamespace(
        usage_metadata={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}
    )
    assert extract_usage(response) == {
        "input_tokens": 100,
        "output_tokens": 20,
        "total_tokens": 120,
    }


def test_summarize_calls_totals_cost():
    calls = [
        {
            "stage": "D2 monologue",
            "model": "gpt-5-2",
            "usage": {"input_tokens": 1_000_000, "output_tokens": 0},
            "cost_usd": cost_usd("gpt-5-2", 1_000_000, 0),
        }
    ]
    summary = summarize_calls(calls)
    assert summary["calls"] == 1
    assert summary["input_tokens"] == 1_000_000
    assert summary["cost_usd"] == cost_usd("gpt-5-2", 1_000_000, 0)
