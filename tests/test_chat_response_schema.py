import pytest
from pydantic import ValidationError

from src.agents.insight_generator import InsightResult
from src.api.v1.schemas.chat import ChatResponse


def test_chat_response_accepts_insight_generator_payload():
    insight = InsightResult(
        summary="Satışlarda artış bekleniyor.",
        chart_data=[
            {"date": "2026-07-01", "predicted_sales": 12000},
            {"date": "2026-07-02", "predicted_sales": 13200},
        ],
        action_plan=["Stok seviyelerini kontrol edin."],
    )

    response = ChatResponse(**insight.to_chat_payload(sql_query="SELECT 1"))

    assert response.status == "success"
    assert response.summary == "Satışlarda artış bekleniyor."
    assert response.sql_query == "SELECT 1"
    assert response.chart_data[0]["date"] == "2026-07-01"
    assert response.action_plan == ["Stok seviyelerini kontrol edin."]
    assert response.sources_queried == []


def test_chat_response_accepts_standard_sources_queried_payload():
    response = ChatResponse(
        status="partial",
        summary="Bazı kaynaklar başarıyla sorgulandı.",
        sql_query=None,
        chart_data=[],
        action_plan=[],
        sources_queried=[
            {
                "source_id": "src_001",
                "alias": "Satış DB",
                "source_type": "postgresql",
                "success": True,
                "row_count": 240,
                "error": None,
            }
        ],
    )

    assert response.status == "partial"
    assert response.sources_queried[0].source_id == "src_001"
    assert response.sources_queried[0].success is True
    assert response.sources_queried[0].row_count == 240


def test_chat_response_rejects_unknown_status():
    with pytest.raises(ValidationError):
        ChatResponse(
            status="ok",
            summary="Geçersiz status.",
            sql_query=None,
            chart_data=[],
            action_plan=[],
        )
