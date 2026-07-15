from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Product
# ---------------------------------------------------------------------------

class ProductBase(BaseModel):
    product_id: str
    product_name: str
    stock_count: int
    critical_threshold: int
    supplier_email: str
    price: float
    available: bool


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    is_critical: bool = False

    @classmethod
    def from_orm_with_flags(cls, obj: object) -> "ProductRead":
        instance = cls.model_validate(obj)
        instance.is_critical = obj.stock_count <= obj.critical_threshold  # type: ignore[union-attr]
        return instance


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------

class OrderBase(BaseModel):
    order_id: int
    customer_name: str
    customer_phone: str
    product_id: str
    quantity: int
    status: str
    cargo_status: str
    estimated_delivery: str
    created_at: datetime


class OrderCreate(BaseModel):
    order_id: int
    customer_name: str
    customer_phone: str = ""
    product_id: str
    quantity: int = 1
    status: str = "Hazırlanıyor"
    cargo_status: str = "Zamanında"
    estimated_delivery: str = ""


class OrderRead(OrderBase):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Shipment
# ---------------------------------------------------------------------------

class ShipmentBase(BaseModel):
    shipment_id: int
    order_id: int
    carrier: str
    tracking_number: str
    actual_status: str
    last_location: str
    delay_days: int
    estimated_delivery: str


class ShipmentCreate(BaseModel):
    shipment_id: int
    order_id: int
    carrier: str = ""
    tracking_number: str = ""
    actual_status: str = "Yolda"
    last_location: str = ""
    delay_days: int = 0
    estimated_delivery: str = ""


class ShipmentRead(ShipmentBase):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Task
# ---------------------------------------------------------------------------

class TaskBase(BaseModel):
    task_id: int
    task_type: str
    description: str
    priority: str
    status: str
    related_order_id: int | None
    related_product_id: str | None


class TaskCreate(BaseModel):
    task_type: str
    description: str
    priority: str = "Orta"
    status: str = "Bekliyor"
    related_order_id: int | None = None
    related_product_id: str | None = None


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Message
# ---------------------------------------------------------------------------

class MessageBase(BaseModel):
    message_id: int
    customer_message: str
    ai_response: str
    intent: str
    status: str
    created_at: datetime


class MessageCreate(BaseModel):
    customer_message: str
    ai_response: str = ""
    intent: str = "GENERAL"
    status: str = "Gönderildi"


class MessageRead(MessageBase):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Chat (Kişi 2 kullanacak)
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message must not be blank")
        return value


class ChatResponse(BaseModel):
    intent: str
    entities: dict
    reply: str
    tool_calls: list[str]
    dashboard_note: str


# ---------------------------------------------------------------------------
# Dashboard Summary
# ---------------------------------------------------------------------------

class DashboardSummary(BaseModel):
    total_orders: int
    preparing_orders: int
    in_cargo_orders: int
    delivered_orders: int
    delayed_orders: int
    critical_stock_products: int
    pending_tasks: int
    ai_summary: str


# ---------------------------------------------------------------------------
# System
# ---------------------------------------------------------------------------

class SeedResponse(BaseModel):
    seeded: bool
    counts: dict[str, int]


class HealthResponse(BaseModel):
    status: str


class BriefingResponse(BaseModel):
    briefing: str
    data: dict
    ai_summary: str | None = None
    tool_calls: list[str] = []


class TaskStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def status_must_be_supported(cls, value: str) -> str:
        allowed = {"Bekliyor", "Onay bekliyor", "Onay Bekliyor", "Tamamlandı"}
        if value not in allowed:
            raise ValueError(f"Unsupported task status: {value}")
        return value
