import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from nexus.engine import Engine
from nexus.llm_research import LLMResearchManager, _extract_json, _valid_context


def test_context_rejects_arbitrary_fields_and_nonfinite_values():
    with pytest.raises(ValueError):
        _valid_context({"account": "secret", "market_decisions": []})
    with pytest.raises(ValueError):
        _valid_context({"as_of": float("nan"), "market_decisions": [], "school_signals": [], "external_facts": []})
    with pytest.raises(ValueError):
        _valid_context({"as_of": 1, "market_decisions": [], "school_signals": [], "external_facts": []})
    with pytest.raises(ValueError):
        _valid_context({"as_of": 1, "market_decisions": [{"symbol": "EURUSD", "balance": 100}], "school_signals": [], "external_facts": []})


def test_output_schema_is_strict_and_shadow_only():
    result = _extract_json(json.dumps({"assessment": "محدود", "observations": ["ملاحظة"], "limitations": []}))
    assert result["authority"] == "SHADOW_RESEARCH_ONLY"
    with pytest.raises(ValueError):
        _extract_json('{"assessment":"trade now","observations":[],"limitations":[],"order":"BUY"}')


def test_unconfigured_provider_state_is_explicit_and_never_calls_network(tmp_path):
    manager = LLMResearchManager(tmp_path / "llm.json", environ={})
    response = manager.run({"as_of": 1, "market_decisions": [{"symbol": "EURUSD", "decision": "WAIT"}], "school_signals": [], "external_facts": []})
    assert response["ok"] is True and response["started"] is False
    state = manager.status()
    assert len(state["providers"]) == 3
    assert {row["status"] for row in state["providers"]} == {"CONFIG_REQUIRED"}
    assert len(state["results"]) == 3
    assert state["providers"][2]["model"] == "openrouter/free"
    assert state["authority"] == "SHADOW_RESEARCH_ONLY"
    assert state["execution_use"] == "NONE"


def test_openai_compatible_provider_uses_fixed_endpoint_and_validates_response(monkeypatch):
    captured = {}

    def fake_read(request):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data)
        captured["authorization"] = request.get_header("Authorization")
        return {"choices": [{"message": {"content": json.dumps({"assessment": "لا استنتاج", "observations": [], "limitations": ["عينة محدودة"]})}}]}

    monkeypatch.setattr("nexus.llm_research._read_response", fake_read)
    provider = {"id": "groq", "name": "Groq", "key": "test-key", "model": "test-model",
                "endpoint": "https://api.groq.com/openai/v1/chat/completions"}
    result = LLMResearchManager._call_provider(provider, '{"market_decisions":[]}')
    assert captured["url"] == provider["endpoint"]
    assert captured["authorization"] == "Bearer test-key"
    assert "function" not in captured["body"] and "tools" not in captured["body"]
    assert result["status"] == "OK"
    assert result["result"]["authority"] == "SHADOW_RESEARCH_ONLY"


def test_provider_endpoint_is_allowlisted(monkeypatch):
    called = False
    def fake_read(_request):
        nonlocal called
        called = True
        return {}
    monkeypatch.setattr("nexus.llm_research._read_response", fake_read)
    provider = {"id": "groq", "name": "Groq", "key": "test-key", "model": "test-model",
                "endpoint": "https://attacker.invalid/collect"}
    with pytest.raises(ValueError):
        LLMResearchManager._call_provider(provider, '{"market_decisions":[]}')
    assert called is False


def test_gemini_provider_uses_api_key_header_not_query_string(monkeypatch):
    captured = {}

    def fake_read(request):
        captured["url"] = request.full_url
        captured["api_key"] = request.get_header("X-goog-api-key")
        captured["body"] = json.loads(request.data)
        return {"candidates": [{"content": {"parts": [{"text": json.dumps({"assessment": "قراءة بحثية", "observations": [], "limitations": []})}]}}]}

    monkeypatch.setattr("nexus.llm_research._read_response", fake_read)
    provider = {"id": "gemini", "name": "Gemini", "key": "secret-key", "model": "gemini-test",
                "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/"}
    result = LLMResearchManager._call_provider(provider, '{"external_facts":[]}')
    assert captured["url"] == provider["endpoint"] + "gemini-test:generateContent"
    assert "secret-key" not in captured["url"]
    assert captured["api_key"] == "secret-key"
    assert result["status"] == "OK"


def test_engine_llm_action_sends_only_allowlisted_research_context(tmp_path):
    root = Path(__file__).resolve().parents[1]
    engine = Engine(root, tmp_path, clock=lambda: 123.0)
    engine.decisions = {"EURUSD": {"decision": "WAIT", "proposals": [], "supporting": [], "opposing": [], "as_of": 122.0}}
    engine.cards_by_symbol = {"EURUSD": [{"strategy_id": "sample", "symbol": "EURUSD", "timeframe": "H1",
                                         "direction": "LONG", "triggered": False, "account": "do-not-send"}]}
    engine.account = {"login": "private"}
    engine.external_research.items = [{"provider": "frankfurter", "kind": "reference_fx_rate",
                                       "rate": 1.1, "observation_date": "2026-10-22", "title": "do-not-send"}]
    engine.llm_research.run = Mock(return_value={"ok": True, "started": False})
    result = engine._action({"action": "run_llm_research"})
    sent = engine.llm_research.run.call_args.args[0]
    assert result["ok"] is True
    assert "account" not in sent and "balance" not in sent and "positions" not in sent and "orders" not in sent
    assert "title" not in json.dumps(sent)
    assert sent["market_decisions"][0]["decision"] == "WAIT"
    assert sent["school_signals"][0]["model"] == "sample"
    assert sent["external_facts"][0]["rate"] == 1.1
    assert engine._empty_state()["llm_research"]["authority"] == "SHADOW_RESEARCH_ONLY"

