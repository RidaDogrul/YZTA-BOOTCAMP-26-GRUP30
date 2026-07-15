from sqlalchemy.orm import Session

from app import crud
from app.models import Order
from app.schemas import DashboardSummary


def get_summary(db: Session, ai_summary: str = "") -> DashboardSummary:
    total = db.query(Order).count()
    preparing = crud.count_orders_by_status(db, "Hazırlanıyor")
    in_cargo = crud.count_orders_by_status(db, "Kargoda")
    delivered = crud.count_orders_by_status(db, "Teslim Edildi")
    delayed = crud.count_delayed_orders(db)
    critical_stock = crud.count_critical_stock(db)
    pending_tasks = crud.count_pending_tasks(db)

    return DashboardSummary(
        total_orders=total,
        preparing_orders=preparing,
        in_cargo_orders=in_cargo,
        delivered_orders=delivered,
        delayed_orders=delayed,
        critical_stock_products=critical_stock,
        pending_tasks=pending_tasks,
        ai_summary=ai_summary,
    )
