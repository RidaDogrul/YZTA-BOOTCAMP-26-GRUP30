from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    product_name: Mapped[str] = mapped_column(String, nullable=False)
    stock_count: Mapped[int] = mapped_column(Integer, default=0)
    critical_threshold: Mapped[int] = mapped_column(Integer, default=10)
    supplier_email: Mapped[str] = mapped_column(String, default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    available: Mapped[bool] = mapped_column(Boolean, default=True)

    orders: Mapped[list["Order"]] = relationship("Order", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_name: Mapped[str] = mapped_column(String, nullable=False)
    customer_phone: Mapped[str] = mapped_column(String, default="")
    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.product_id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String, default="Hazırlanıyor")
    cargo_status: Mapped[str] = mapped_column(String, default="Zamanında")
    estimated_delivery: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    product: Mapped["Product"] = relationship("Product", back_populates="orders")
    shipment: Mapped["Shipment"] = relationship("Shipment", back_populates="order", uselist=False)


class Shipment(Base):
    __tablename__ = "shipments"

    shipment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.order_id"))
    carrier: Mapped[str] = mapped_column(String, default="")
    tracking_number: Mapped[str] = mapped_column(String, default="")
    actual_status: Mapped[str] = mapped_column(String, default="Yolda")
    last_location: Mapped[str] = mapped_column(String, default="")
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    estimated_delivery: Mapped[str] = mapped_column(String, default="")

    order: Mapped["Order"] = relationship("Order", back_populates="shipment")


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_type: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String, default="Orta")
    status: Mapped[str] = mapped_column(String, default="Bekliyor")
    related_order_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    related_product_id: Mapped[str | None] = mapped_column(String, nullable=True)


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_message: Mapped[str] = mapped_column(Text, default="")
    ai_response: Mapped[str] = mapped_column(Text, default="")
    intent: Mapped[str] = mapped_column(String, default="GENERAL")
    status: Mapped[str] = mapped_column(String, default="Gönderildi")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
