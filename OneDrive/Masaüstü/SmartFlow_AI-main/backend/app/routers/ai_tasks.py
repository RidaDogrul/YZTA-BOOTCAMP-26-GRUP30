from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import google.generativeai as genai

from app.config import settings
from app.database import get_db
from app.tools import generate_daily_briefing
from app.schemas import BriefingResponse

router = APIRouter(prefix="/api/tasks", tags=["ai"])

_briefing_cache: dict = {}


def _fallback_briefing(data: dict) -> str:
    summary = data.get("summary", {})
    delayed = data.get("delayed_orders", [])
    critical = data.get("critical_products", [])
    pending = data.get("pending_tasks", [])

    lines = [
        "Bugünkü Operasyon Özeti:",
        f"- Bugün toplam {summary.get('total_orders', 0)} aktif sipariş var.",
        f"- {summary.get('preparing_orders', 0)} sipariş hazırlanmayı bekliyor.",
        f"- {summary.get('in_cargo_orders', 0)} sipariş kargoda.",
        f"- {len(delayed)} siparişte gecikme riski bulunuyor.",
        f"- {len(critical)} ürün kritik stok seviyesinde.",
    ]
    if pending:
        lines.append("- Öncelikli görevler:")
        for index, task in enumerate(pending[:3], start=1):
            lines.append(f"  {index}. {task['description']}")
    return "\n".join(lines)


@router.post("/generate", response_model=BriefingResponse)
def generate_tasks(db: Session = Depends(get_db)):
    today = str(date.today())
    if _briefing_cache.get("date") == today:
        return _briefing_cache["result"]

    data = generate_daily_briefing(db)
    tool_calls = ["generate_daily_briefing", "check_stock_alerts"]
    briefing_text = ""

    if settings.GEMINI_API_KEY:
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel(settings.GEMINI_MODEL)
            prompt = f"""
Aşağıdaki işletme verisine göre bugünkü operasyon brifingi yaz.
Türkçe, madde madde, yönetici için kısa ve net olsun.
Veri: {data}
"""
            response = model.generate_content(prompt)
            briefing_text = response.candidates[0].content.parts[0].text
        except Exception:
            briefing_text = ""

    if not briefing_text:
        briefing_text = _fallback_briefing(data)

    result = BriefingResponse(
        briefing=briefing_text,
        ai_summary=briefing_text,
        data=data,
        tool_calls=tool_calls,
    )
    _briefing_cache["date"] = today
    _briefing_cache["result"] = result
    return result
