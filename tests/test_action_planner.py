import json
from types import SimpleNamespace

import pytest

import src.agents.tools.action_planner as planner_module
from src.agents.tools.action_planner import ActionPlanner


class FakeLLM:
    def __init__(self, content: str | None = None, error: Exception | None = None) -> None:
        self.content = content
        self.error = error
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            content=self.content,
            usage_metadata={
                "input_tokens": 100,
                "output_tokens": 25,
                "total_tokens": 125,
            },
            response_metadata={"model_name": "fake-action-model"},
        )


def build_llm_response(
    *,
    action: str = "Düşüş beklenen ürün için hedefli kampanya başlatın.",
    reason: str = "Doğrulanmış tahmin azalış gösteriyor.",
    priority: str = "high",
    reasoning: str = "Tahmin eğilimi aksiyon gerektiriyor.",
) -> str:
    return json.dumps(
        {
            "reasoning": reasoning,
            "actions": [
                {
                    "action": action,
                    "reason": reason,
                    "priority": priority,
                }
            ],
        },
        ensure_ascii=False,
    )


def test_decline_metrics_produce_llm_action_plan(monkeypatch) -> None:
    llm = FakeLLM(content=build_llm_response())
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(
        question="Gelecek ay satışlar nasıl olacak?",
        summary="Satışlarda düşüş bekleniyor.",
        metrics={
            "trend": "azalış",
            "change_percent": -12.5,
            "mape_percent": 6.4,
        },
    )

    assert result.success is True
    assert result.source == "llm"
    assert result.trend == "decrease"
    assert result.risk_level == "low"
    assert result.action_plan == ["Düşüş beklenen ürün için hedefli kampanya başlatın."]
    assert result.actions[0].priority == "high"
    assert llm.messages is not None


def test_chart_data_can_derive_increasing_trend(monkeypatch) -> None:
    llm = FakeLLM(
        content=build_llm_response(
            action="Büyüyen talep için operasyon kapasitesini hazırlayın.",
            reason="Tahmin serisi artış gösteriyor.",
        )
    )
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(
        question="Talep nasıl değişecek?",
        chart_data=[{"yhat": 100.0}, {"yhat": 120.0}],
    )

    assert result.trend == "increase"
    assert result.risk_level == "medium"
    assert result.source == "llm"


def test_high_mape_produces_high_decision_risk(monkeypatch) -> None:
    llm = FakeLLM(content=build_llm_response())
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(
        question="Tahmine göre ne yapmalıyız?",
        metrics={"trend": "azalış", "mape_percent": 25.0},
    )

    assert result.risk_level == "high"


def test_fenced_json_is_parsed(monkeypatch) -> None:
    llm = FakeLLM(content=f"```json\n{build_llm_response()}\n```")
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(question="Ne yapmalıyız?", metrics={"trend": "yatay"})

    assert result.source == "llm"
    assert len(result.actions) == 1


def test_string_actions_are_normalized(monkeypatch) -> None:
    response = json.dumps(
        {
            "reasoning": "Mevcut plan izlenmeli.",
            "actions": ["Mevcut stratejiyi koruyup sapmaları izleyin."],
        },
        ensure_ascii=False,
    )
    llm = FakeLLM(content=response)
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(question="Ne yapmalıyız?", metrics={"trend": "yatay"})

    assert result.action_plan == ["Mevcut stratejiyi koruyup sapmaları izleyin."]
    assert result.actions[0].priority == "medium"


def test_malformed_json_uses_safe_fallback(monkeypatch) -> None:
    llm = FakeLLM(content="JSON olmayan model yanıtı")
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(
        question="Satış düşüşünde ne yapmalıyız?",
        metrics={"trend": "azalış", "mape_percent": 7.0},
    )

    assert result.success is False
    assert result.source == "fallback"
    assert result.trend == "decrease"
    assert any("kampanya" in action.casefold() for action in result.action_plan)


def test_llm_exception_uses_english_fallback(monkeypatch) -> None:
    llm = FakeLLM(error=RuntimeError("model unavailable"))
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(
        question="What should we do?",
        metrics={"trend": "increase", "mape_percent": 8.0},
        language="en",
    )

    assert result.source == "fallback"
    assert result.trend == "increase"
    assert any("capacity" in action.casefold() for action in result.action_plan)


def test_invented_number_forces_fallback(monkeypatch) -> None:
    llm = FakeLLM(
        content=build_llm_response(
            action="Kampanya bütçesini yüzde 50 artırın.",
            reason="Satışlarda düşüş bekleniyor.",
        )
    )
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(
        question="Ne yapmalıyız?",
        metrics={"trend": "azalış", "change_percent": -12.5},
    )

    assert result.source == "fallback"
    assert result.error is not None
    assert "50" in result.error


def test_existing_number_is_allowed(monkeypatch) -> None:
    llm = FakeLLM(
        content=build_llm_response(
            action="Beklenen yüzde 12,5 düşüş için kampanya pilotu başlatın.",
            reason="Doğrulanmış değişim yüzde 12,5 düşüş gösteriyor.",
        )
    )
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(
        question="Ne yapmalıyız?",
        metrics={"trend": "azalış", "change_percent": -12.5},
    )

    assert result.source == "llm"


def test_duplicate_actions_are_removed(monkeypatch) -> None:
    action = "Talep değişimini yakından izleyin."
    response = json.dumps(
        {
            "reasoning": "İzleme gerekli.",
            "actions": [action, action],
        },
        ensure_ascii=False,
    )
    llm = FakeLLM(content=response)
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    result = planner.run(question="Ne yapmalıyız?", metrics={"trend": "yatay"})

    assert result.action_plan == [action]


def test_candidate_actions_are_sent_as_context(monkeypatch) -> None:
    llm = FakeLLM(content=build_llm_response())
    monkeypatch.setattr(planner_module, "log_token_usage", lambda response: None)
    planner = ActionPlanner(llm=llm)

    planner.run(
        question="Ne yapmalıyız?",
        candidate_actions=["H1 tarafından önerilen kampanyayı değerlendirin."],
    )

    assert llm.messages is not None
    human_message = json.loads(llm.messages[1].content)
    assert human_message["candidate_actions"] == [
        "H1 tarafından önerilen kampanyayı değerlendirin."
    ]


def test_token_usage_is_logged(monkeypatch) -> None:
    llm = FakeLLM(content=build_llm_response())
    captured: list[object] = []
    monkeypatch.setattr(
        planner_module,
        "log_token_usage",
        lambda response: captured.append(response),
    )
    planner = ActionPlanner(llm=llm)

    planner.run(question="Ne yapmalıyız?", metrics={"trend": "azalış"})

    assert len(captured) == 1


def test_empty_question_is_rejected() -> None:
    planner = ActionPlanner(llm=FakeLLM(content=build_llm_response()))

    with pytest.raises(ValueError, match="question boş olamaz"):
        planner.run(question="   ")


def test_invalid_language_is_rejected() -> None:
    planner = ActionPlanner(llm=FakeLLM(content=build_llm_response()))

    with pytest.raises(ValueError, match="language"):
        planner.run(question="Ne yapmalıyız?", language="de")  # type: ignore[arg-type]
