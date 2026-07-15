import google.generativeai as genai
from sqlalchemy.orm import Session

from app.config import settings
from app.tools import (
    get_order_status, get_product_info, get_cargo_status,
    check_stock_alerts, draft_supplier_email,
    generate_daily_briefing, send_manager_alert,
    TOOL_DECLARATIONS,
)
from app import crud

genai.configure(api_key=settings.GEMINI_API_KEY)

SYSTEM_PROMPT = """Sen SmartFlow AI'sın. KOBİ'lere yönelik bir operasyon asistanısın.
Müşteri mesajlarını Türkçe olarak anlayıp cevapla.
ASLA tahmin yürütme — önce ilgili tool'u çağır, gelen veriye göre cevap ver.
Cevapların kısa, nazik ve profesyonel olsun."""

TOOL_MAP = {
    "get_order_status": get_order_status,
    "get_product_info": get_product_info,
    "get_cargo_status": get_cargo_status,
    "check_stock_alerts": check_stock_alerts,
    "draft_supplier_email": draft_supplier_email,
    "generate_daily_briefing": generate_daily_briefing,
    "send_manager_alert": send_manager_alert,
}

DB_TOOLS = {
    "get_order_status", "get_product_info", "get_cargo_status",
    "check_stock_alerts", "draft_supplier_email", "generate_daily_briefing"
}


def _process_chat_real(message: str, db: Session) -> dict:
    model = genai.GenerativeModel(
        model_name=settings.GEMINI_MODEL,
        system_instruction=SYSTEM_PROMPT,
        tools=TOOL_DECLARATIONS,
    )

    tool_calls_used = []
    dashboard_notes = []

    response = model.generate_content(message)

    for _ in range(3):
        part = response.candidates[0].content.parts[0]

        if not hasattr(part, "function_call") or not part.function_call.name:
            break

        fn_name = part.function_call.name
        fn_args = dict(part.function_call.args)
        tool_calls_used.append(fn_name)

        fn = TOOL_MAP[fn_name]
        if fn_name in DB_TOOLS:
            fn_result = fn(db, **fn_args)
        else:
            fn_result = fn(**fn_args)

        if fn_name in ("get_order_status", "get_cargo_status"):
            if fn_result.get("delay_days", 0) > 0:
                oid = fn_args.get("order_id")
                dashboard_notes.append(f"{oid} numaralı sipariş için gecikme uyarısı oluşturuldu.")

        response = model.generate_content([
            {"role": "user", "parts": [message]},
            {"role": "model", "parts": [part]},
            {
                "role": "user",
                "parts": [{
                    "function_response": {
                        "name": fn_name,
                        "response": fn_result,
                    }
                }]
            }
        ])

    final_text = response.candidates[0].content.parts[0].text

    intent = _detect_intent(message, tool_calls_used)
    entities = _extract_entities(message, db)

    crud.create_message(db, customer_message=message, ai_response=final_text, intent=intent)

    return {
        "intent": intent,
        "entities": entities,
        "reply": final_text,
        "tool_calls": tool_calls_used,
        "dashboard_note": "; ".join(dashboard_notes) if dashboard_notes else "",
    }


def _detect_intent(message: str, tool_calls: list[str]) -> str:
    if "get_cargo_status" in tool_calls:
        return "CARGO_STATUS"
    if "get_order_status" in tool_calls:
        return "ORDER_STATUS"
    if "get_product_info" in tool_calls:
        return "PRODUCT_INFO"
    if "check_stock_alerts" in tool_calls:
        return "STOCK_ALERT"
    if "generate_daily_briefing" in tool_calls:
        return "DAILY_BRIEFING"
    msg = message.lower()
    if any(w in msg for w in ["kargo", "gecik", "neden gelmedi", "gelmedi"]):
        return "CARGO_STATUS"
    if any(w in msg for w in ["sipariş", "nerede", "geldi mi"]):
        return "ORDER_STATUS"
    if any(w in msg for w in ["kritik stok", "kritik ürün"]):
        return "STOCK_ALERT"
    if any(w in msg for w in ["stok", "var mı", "kaç adet", "ürün"]):
        return "PRODUCT_INFO"
    if any(w in msg for w in ["özet", "brifing", "bugün"]):
        return "DAILY_BRIEFING"
    return "GENERAL"


def _extract_entities(message: str, db: Session | None = None) -> dict:
    import re
    entities = {}
    match = re.search(r'\b(\d{3,})\b', message)
    if match:
        entities["order_id"] = int(match.group(1))
    if db:
        product = _find_product_in_message(message, db)
        if product:
            entities["product_name"] = product.product_name
            entities["product_id"] = product.product_id
    return entities


def _find_product_in_message(message: str, db: Session):
    normalized = message.casefold()
    for product in crud.get_products(db):
        if product.product_name.casefold() in normalized:
            return product
    return None


def _format_daily_briefing(data: dict) -> str:
    summary = data.get("summary", {})
    delayed = data.get("delayed_orders", [])
    critical = data.get("critical_products", [])
    pending = data.get("pending_tasks", [])
    lines = [
        f"Bugün {summary.get('total_orders', 0)} sipariş var.",
        f"{summary.get('preparing_orders', 0)} sipariş hazırlanmayı bekliyor.",
        f"{len(delayed)} kargo gecikmiş.",
        f"{len(critical)} ürün kritik stokta.",
    ]
    if pending:
        tasks = ", ".join(task["description"] for task in pending[:3])
        lines.append(f"Öncelikli görevler: {tasks}")
    return " ".join(lines)


def _process_chat_fallback(message: str, db: Session, error: Exception | None = None) -> dict:
    intent = _detect_intent(message, [])
    entities = _extract_entities(message, db)
    tool_calls: list[str] = []
    dashboard_note = ""

    if intent == "CARGO_STATUS" and entities.get("order_id"):
        order_id = entities["order_id"]
        order_data = get_order_status(db, order_id)
        cargo_data = get_cargo_status(db, order_id)
        tool_calls = ["get_order_status", "get_cargo_status"]
        if "error" in cargo_data:
            reply = cargo_data["error"]
        else:
            delay_days = cargo_data.get("delay_days", 0)
            delay_text = f"{delay_days} günlük gecikme" if delay_days else "gecikme görünmüyor"
            reply = (
                f"{order_id} numaralı siparişiniz için {delay_text}. "
                f"Paketiniz {cargo_data.get('last_location', 'kargo sürecinde')} konumunda, "
                f"tahmini teslimat {cargo_data.get('estimated_delivery', order_data.get('estimated_delivery', 'belirtilmemiş'))}."
            )
            if delay_days:
                dashboard_note = f"{order_id} numaralı sipariş için gecikme uyarısı oluşturuldu."
    elif intent == "ORDER_STATUS" and entities.get("order_id"):
        order_id = entities["order_id"]
        data = get_order_status(db, order_id)
        tool_calls = ["get_order_status"]
        if "error" in data:
            reply = data["error"]
        else:
            reply = (
                f"{order_id} numaralı siparişiniz {data.get('status')} durumunda. "
                f"Kargo durumu: {data.get('cargo_status')}. "
                f"Tahmini teslimat {data.get('estimated_delivery')}."
            )
    elif intent == "STOCK_ALERT":
        data = check_stock_alerts(db)
        tool_calls = ["check_stock_alerts"]
        products = data.get("products", [])
        if products:
            items = ", ".join(
                f"{p['product_name']} ({p['stock_count']}/{p['critical_threshold']})"
                for p in products
            )
            reply = f"Kritik stokta {len(products)} ürün var: {items}."
        else:
            reply = "Şu anda kritik stok seviyesinde ürün görünmüyor."
    elif intent == "PRODUCT_INFO":
        product = _find_product_in_message(message, db)
        if product:
            data = get_product_info(db, product.product_name)
            tool_calls = ["get_product_info"]
            critical_note = " Kritik seviyede görünüyor." if data.get("is_critical") else ""
            reply = (
                f"Evet, {data['product_name']} stokta mevcut. "
                f"Şu anda {data['stock_count']} adet bulunmaktadır.{critical_note}"
            )
        else:
            reply = "Ürün adını netleştirirseniz stok bilgisini kontrol edebilirim."
    elif intent == "DAILY_BRIEFING":
        data = generate_daily_briefing(db)
        tool_calls = ["generate_daily_briefing"]
        reply = _format_daily_briefing(data)
    else:
        reply = "Merhaba! Sipariş, kargo, stok veya günlük operasyon özeti için yardımcı olabilirim."

    if error:
        dashboard_note = dashboard_note or f"[FALLBACK] Gemini API hatası: {str(error)[:60]}"

    crud.create_message(db, customer_message=message, ai_response=reply, intent=intent)
    return {
        "intent": intent,
        "entities": entities,
        "reply": reply,
        "tool_calls": tool_calls,
        "dashboard_note": dashboard_note,
    }


def process_chat(message: str, db: Session) -> dict:
    if not settings.GEMINI_API_KEY:
        return _process_chat_fallback(message, db)
    try:
        return _process_chat_real(message, db)
    except Exception as e:
        return _process_chat_fallback(message, db, e)
