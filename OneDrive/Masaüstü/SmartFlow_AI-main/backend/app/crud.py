from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Message, Order, Product, Shipment, Task


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def get_orders(db: Session) -> list[Order]:
    return db.query(Order).order_by(Order.created_at.desc()).all()


def get_order(db: Session, order_id: int) -> Order | None:
    return db.query(Order).filter(Order.order_id == order_id).first()


def get_orders_by_status(db: Session, status: str) -> list[Order]:
    return db.query(Order).filter(Order.status == status).all()


def get_delayed_orders(db: Session) -> list[Order]:
    return db.query(Order).filter(Order.cargo_status == "Gecikmiş").all()


def count_orders_by_status(db: Session, status: str) -> int:
    return db.query(func.count(Order.order_id)).filter(Order.status == status).scalar() or 0


def count_delayed_orders(db: Session) -> int:
    return db.query(func.count(Order.order_id)).filter(Order.cargo_status == "Gecikmiş").scalar() or 0


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

def get_products(db: Session) -> list[Product]:
    return db.query(Product).all()


def get_product(db: Session, product_id: str) -> Product | None:
    return db.query(Product).filter(Product.product_id == product_id).first()


def get_product_by_name(db: Session, name: str) -> Product | None:
    return db.query(Product).filter(
        func.lower(Product.product_name).contains(name.lower())
    ).first()


def get_critical_stock_products(db: Session) -> list[Product]:
    return db.query(Product).filter(Product.stock_count <= Product.critical_threshold).all()


def count_critical_stock(db: Session) -> int:
    return db.query(func.count(Product.product_id)).filter(
        Product.stock_count <= Product.critical_threshold
    ).scalar() or 0


# ---------------------------------------------------------------------------
# Shipments
# ---------------------------------------------------------------------------

def get_shipments(db: Session) -> list[Shipment]:
    return db.query(Shipment).all()


def get_shipment_by_order(db: Session, order_id: int) -> Shipment | None:
    return db.query(Shipment).filter(Shipment.order_id == order_id).first()


def get_order_with_shipment(db: Session, order_id: int) -> tuple[Order | None, Shipment | None]:
    order = get_order(db, order_id)
    shipment = get_shipment_by_order(db, order_id) if order else None
    return order, shipment


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

def get_tasks(db: Session) -> list[Task]:
    return db.query(Task).order_by(Task.task_id).all()


def get_task(db: Session, task_id: int) -> Task | None:
    return db.query(Task).filter(Task.task_id == task_id).first()


def create_task(db: Session, task_type: str, description: str, priority: str,
                status: str = "Bekliyor", related_order_id: int | None = None,
                related_product_id: str | None = None) -> Task:
    task = Task(
        task_type=task_type,
        description=description,
        priority=priority,
        status=status,
        related_order_id=related_order_id,
        related_product_id=related_product_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_task_status(db: Session, task_id: int, status: str) -> Task | None:
    task = get_task(db, task_id)
    if not task:
        return None
    task.status = status
    db.commit()
    db.refresh(task)
    return task


def count_pending_tasks(db: Session) -> int:
    return db.query(func.count(Task.task_id)).filter(Task.status == "Bekliyor").scalar() or 0


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

def get_messages(db: Session, limit: int = 50) -> list[Message]:
    return db.query(Message).order_by(Message.created_at.desc()).limit(limit).all()


def create_message(db: Session, customer_message: str, ai_response: str,
                   intent: str = "GENERAL", status: str = "Gönderildi") -> Message:
    msg = Message(
        customer_message=customer_message,
        ai_response=ai_response,
        intent=intent,
        status=status,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
