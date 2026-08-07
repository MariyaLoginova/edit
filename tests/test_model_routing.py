from __future__ import annotations

import pytest

from edit.model_routing import FailoverChatModel, is_policy_error


def test_policy_error_is_detected():
    assert is_policy_error(
        RuntimeError("prompt contains sensitive words that violate Generative AI Prohibited Use policy")
    )
    assert not is_policy_error(RuntimeError("timeout"))


def test_failover_switches_once_only_for_policy(monkeypatch):
    class Working:
        def invoke(self, messages):
            return {"content": "ok"}

    def factory(*, model, temperature):
        if model == "blocked":
            class Blocked:
                def invoke(self, messages):
                    raise RuntimeError("sensitive words violate prohibited use policy")

            return Blocked()
        return Working()

    monkeypatch.setattr("edit.model_routing.get_chat_model", factory)
    router = FailoverChatModel(["blocked", "working"])
    assert router.invoke([]) == {"content": "ok"}
    assert router.disabled_models == {"blocked"}
    assert router.events[0]["kind"] == "policy_block"


def test_failover_does_not_retry_transient_error(monkeypatch):
    def factory(*, model, temperature):
        class Broken:
            def invoke(self, messages):
                raise RuntimeError("provider timeout")

        return Broken()

    monkeypatch.setattr("edit.model_routing.get_chat_model", factory)
    router = FailoverChatModel(["first", "second"])
    with pytest.raises(RuntimeError, match="timeout"):
        router.invoke([])
    assert router.disabled_models == set()


def test_failover_switches_when_policy_is_returned_as_content(monkeypatch):
    def factory(*, model, temperature):
        class Response:
            content = "The prompt contains sensitive words that violate Prohibited Use policy."

        class Blocked:
            def invoke(self, messages):
                return Response()

        class Working:
            def invoke(self, messages):
                return {"content": "ok"}

        return Blocked() if model == "blocked" else Working()

    monkeypatch.setattr("edit.model_routing.get_chat_model", factory)
    router = FailoverChatModel(["blocked", "working"])
    assert router.invoke([]) == {"content": "ok"}
    assert router.disabled_models == {"blocked"}
