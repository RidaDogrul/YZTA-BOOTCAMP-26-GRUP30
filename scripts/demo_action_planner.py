"""Sprint 3 H2 Action Planner çevrimdışı demosu."""

from __future__ import annotations

import json
from types import SimpleNamespace

from src.agents.tools.action_planner import ActionPlanner


class DemoLLM:
    """API anahtarı kullanmadan Action Planner akışını gösteren sahte LLM."""

    def invoke(self, messages):
        return SimpleNamespace(
            content=json.dumps(
                {
                    "reasoning": (
                        "Tahmin, ilgili ürün grubunda doğrulanmış bir düşüşe "
                        "işaret ettiği için talep ve stok riski birlikte yönetilmelidir."
                    ),
                    "actions": [
                        {
                            "action": (
                                "Kayıp beklenen ürün grubu için hedefli bir kampanya pilotu başlatın."
                            ),
                            "reason": "Tahmin eğilimi azalış gösteriyor.",
                            "priority": "high",
                        },
                        {
                            "action": (
                                "Stok ve satın alma planını beklenen talep düşüşüne göre gözden geçirin."
                            ),
                            "reason": "Fazla stok riskini sınırlamak gerekiyor.",
                            "priority": "high",
                        },
                    ],
                },
                ensure_ascii=False,
            ),
            usage_metadata={
                "input_tokens": 420,
                "output_tokens": 95,
                "total_tokens": 515,
            },
            response_metadata={"model_name": "demo-action-model"},
        )


def main() -> None:
    planner = ActionPlanner(llm=DemoLLM())
    result = planner.run(
        question="Önümüzdeki ay düşüş beklenen ürünler için ne yapmalıyız?",
        summary="Tahmin, ilgili ürün grubunda satış kaybı beklendiğini gösteriyor.",
        metrics={
            "selected_model": "prophet",
            "mape_percent": 6.4,
            "change_percent": -12.5,
            "trend": "azalış",
            "has_prediction_intervals": True,
        },
        chart_data=[
            {"ds": "2026-08-01", "yhat": 100.0},
            {"ds": "2026-08-30", "yhat": 87.5},
        ],
    )

    print("ACTION PLANNER SONUCU")
    print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
