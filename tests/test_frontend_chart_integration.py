from pathlib import Path


def test_chart_js_exposes_chart_integration_helpers():
    chart_js = Path("frontend/chat/js/chart.js").read_text(encoding="utf-8")

    assert "function normalizeChartData(data)" in chart_js
    assert "function buildChartConfig(data)" in chart_js
    assert "function renderChart(container, chartData, chartId)" in chart_js
    assert "window.DataCleanroomCharts" in chart_js


def test_chart_js_handles_invalid_and_oversized_payloads():
    chart_js = Path("frontend/chat/js/chart.js").read_text(encoding="utf-8")

    assert "const MAX_CHART_POINTS = 120" in chart_js
    assert "if (!Array.isArray(data)) return [];" in chart_js
    assert ".slice(0, MAX_CHART_POINTS)" in chart_js
    assert "chart_data formatı desteklenmiyor" in chart_js


def test_chat_ui_wires_api_chart_data_to_renderer():
    chat_js = Path("frontend/chat/js/chat.js").read_text(encoding="utf-8")

    assert "chartData:  response.chart_data || []" in chat_js
    assert "if (Array.isArray(chartData) && chartData.length > 0)" in chat_js
    assert "renderChart(wrapper, chartData, id)" in chat_js
