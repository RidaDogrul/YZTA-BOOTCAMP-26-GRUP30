# SmartFlow AI Mimari

```text
Müşteri Chat / Yönetici Dashboard
        |
      FastAPI
        |
 Gemini AI Agent + Tool Dispatcher
        |
 SQLAlchemy / SQLite
        |
 Orders, Products, Shipments, Tasks, Messages
```

## Ana Bileşenler

- `backend/app/main.py`: FastAPI uygulaması, CORS, router kayıtları ve startup seed akışı.
- `backend/app/ai_service.py`: Gemini çağrısı, tool dispatch döngüsü, intent/entity fallback ve mesaj kaydı.
- `backend/app/tools.py`: `get_order_status`, `get_product_info`, `get_cargo_status`, `check_stock_alerts`, `draft_supplier_email`, `generate_daily_briefing`, `send_manager_alert`.
- `backend/app/dashboard_service.py`: dashboard özet metrikleri.
- `backend/app/email_service.py`: Resend üzerinden yönetici uyarısı.
- `frontend/chat.html`: tek dosyalık müşteri chat demosu.
- `frontend/dashboard.html`: tek dosyalık yönetici dashboard demosu.
- `frontend/src`: Vite + React ile ek yönetici arayüzü.

## Veri Akışı

1. Kullanıcı mesajı `/api/chat` endpointine gelir.
2. Gemini intent/entity çıkarır ve uygun tool'u çağırır.
3. Tool fonksiyonu SQLite verisini SQLAlchemy ile sorgular.
4. AI veri destekli müşteri cevabı üretir.
5. Mesaj `messages` tablosuna kaydedilir ve gerekirse dashboard notu döner.

Gemini API kullanılamadığında aynı tool fonksiyonları deterministic fallback tarafından çağrılır; demo akışı bu yüzden API anahtarı olmadan da çalışır.
