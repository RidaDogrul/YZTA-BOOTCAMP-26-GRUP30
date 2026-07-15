from sqlalchemy.orm import Session
from app import crud
import google.generativeai as genai


def get_order_status(db: Session, order_id: int) -> dict:
    order, shipment = crud.get_order_with_shipment(db, order_id)
    if not order:
        return {"error": f"Sipariş bulunamadı: {order_id}"}
    result = {
        "order_id": order.order_id,
        "customer_name": order.customer_name,
        "status": order.status,
        "cargo_status": order.cargo_status,
        "estimated_delivery": order.estimated_delivery,
        "product_id": order.product_id,
    }
    if shipment:
        result["carrier"] = shipment.carrier
        result["last_location"] = shipment.last_location
        result["delay_days"] = shipment.delay_days
    return result


def get_product_info(db: Session, product_name: str) -> dict:
    product = crud.get_product_by_name(db, product_name)
    if not product:
        return {"error": f"Ürün bulunamadı: {product_name}"}
    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "stock_count": product.stock_count,
        "critical_threshold": product.critical_threshold,
        "is_critical": product.stock_count <= product.critical_threshold,
        "available": product.available,
        "price": product.price,
    }


def get_cargo_status(db: Session, order_id: int) -> dict:
    shipment = crud.get_shipment_by_order(db, order_id)
    if not shipment:
        return {"error": f"Kargo kaydı bulunamadı: {order_id}"}
    return {
        "order_id": order_id,
        "actual_status": shipment.actual_status,
        "carrier": shipment.carrier,
        "tracking_number": shipment.tracking_number,
        "last_location": shipment.last_location,
        "delay_days": shipment.delay_days,
        "estimated_delivery": shipment.estimated_delivery,
    }


def check_stock_alerts(db: Session) -> dict:
    products = crud.get_critical_stock_products(db)
    return {
        "critical_count": len(products),
        "products": [
            {
                "product_id": p.product_id,
                "product_name": p.product_name,
                "stock_count": p.stock_count,
                "critical_threshold": p.critical_threshold,
                "supplier_email": p.supplier_email,
            }
            for p in products
        ],
    }


def draft_supplier_email(db: Session, product_id: str) -> dict:
    product = crud.get_product(db, product_id)
    if not product:
        return {"error": f"Ürün bulunamadı: {product_id}"}
    subject = f"{product.product_name} Stok Yenileme Talebi"
    body = (
        f"Merhaba,\n\n"
        f"{product.product_name} ürünümüzün stoğu kritik seviyeye düşmüştür "
        f"(mevcut: {product.stock_count} adet, eşik: {product.critical_threshold} adet).\n"
        f"En kısa sürede yeni tedarik için fiyat ve teslim süresi bilgisini paylaşabilir misiniz?\n\n"
        f"Teşekkürler."
    )
    return {
        "to": product.supplier_email,
        "subject": subject,
        "body": body,
        "product_name": product.product_name,
    }


def generate_daily_briefing(db: Session) -> dict:
    from app.dashboard_service import get_summary
    from app import crud as c
    summary = get_summary(db)
    delayed = c.get_delayed_orders(db)
    critical = c.get_critical_stock_products(db)
    tasks = c.get_tasks(db)
    return {
        "summary": summary.model_dump(),
        "delayed_orders": [{"order_id": o.order_id, "customer_name": o.customer_name} for o in delayed],
        "critical_products": [{"product_name": p.product_name, "stock_count": p.stock_count} for p in critical],
        "pending_tasks": [
            {"task_id": t.task_id, "description": t.description, "priority": t.priority}
            for t in tasks if t.status == "Bekliyor"
        ],
    }


def send_manager_alert(order_id: int, message: str) -> dict:
    from app.email_service import send_manager_alert_email
    subject = f"Yönetici Uyarısı — Sipariş #{order_id}"
    body = f"Sipariş #{order_id} için uyarı:\n\n{message}"
    sent = send_manager_alert_email(subject, body)
    return {"sent": sent, "order_id": order_id}


TOOL_DECLARATIONS = [
    genai.protos.Tool(
        function_declarations=[
            genai.protos.FunctionDeclaration(
                name="get_order_status",
                description="Verilen sipariş numarasının durumunu, kargo bilgisini ve tahmini teslimatını getirir.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "order_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Sipariş numarası"
                        )
                    },
                    required=["order_id"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_product_info",
                description="Verilen ürün adının stok bilgisini getirir.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "product_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Ürün adı (kısmi eşleşme desteklenir)"
                        )
                    },
                    required=["product_name"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_cargo_status",
                description="Verilen sipariş numarasının kargo durumunu ve takip bilgisini getirir.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "order_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Sipariş numarası"
                        )
                    },
                    required=["order_id"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="check_stock_alerts",
                description="Kritik stok seviyesine düşmüş tüm ürünleri listeler.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={}
                )
            ),
            genai.protos.FunctionDeclaration(
                name="draft_supplier_email",
                description="Verilen ürün ID'si için tedarikçiye gönderilecek e-posta taslağını oluşturur.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "product_id": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Ürün ID'si (örn: P002)"
                        )
                    },
                    required=["product_id"]
                )
            ),
            genai.protos.FunctionDeclaration(
                name="generate_daily_briefing",
                description="Günlük operasyon özetini oluşturur: gecikmiş siparişler, kritik stoklar, bekleyen görevler.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={}
                )
            ),
            genai.protos.FunctionDeclaration(
                name="send_manager_alert",
                description="Yöneticiye e-posta uyarısı gönderir.",
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "order_id": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="İlgili sipariş numarası"
                        ),
                        "message": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Uyarı mesajı"
                        )
                    },
                    required=["order_id", "message"]
                )
            ),
        ]
    )
]
