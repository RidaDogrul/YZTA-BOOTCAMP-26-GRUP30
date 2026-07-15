# SmartFlow AI API Tasarımı

| Method | Endpoint | Açıklama |
|---|---|---|
| GET | `/health` | Sağlık kontrolü |
| POST | `/api/seed` | Demo verisini sıfırlar |
| GET | `/api/orders` | Siparişleri listeler |
| GET | `/api/orders/{order_id}` | Tek sipariş detayını getirir |
| GET | `/api/products` | Ürünleri listeler |
| GET | `/api/shipments` | Kargo kayıtlarını listeler |
| GET | `/api/tasks` | Görevleri listeler |
| PATCH | `/api/tasks/{task_id}` | Görev durumunu günceller |
| POST | `/api/tasks/generate` | Günlük operasyon brifingi üretir ve cache'ler |
| GET | `/api/dashboard/summary` | Dashboard özet metriklerini getirir |
| GET | `/api/messages` | Chat mesaj geçmişini listeler |
| POST | `/api/chat` | Müşteri mesajını AI/tool akışıyla cevaplar |
| POST | `/api/alerts/send` | Yönetici e-posta uyarısı gönderir |

## POST /api/chat

Request:

```json
{
  "message": "142 numaralı siparişim neden gelmedi?"
}
```

Response:

```json
{
  "intent": "CARGO_STATUS",
  "entities": {
    "order_id": 142
  },
  "reply": "142 numaralı siparişiniz için 2 günlük gecikme...",
  "tool_calls": ["get_order_status", "get_cargo_status"],
  "dashboard_note": "142 numaralı sipariş için gecikme uyarısı oluşturuldu."
}
```

## POST /api/tasks/generate

Gemini API anahtarı varsa Gemini ile yönetici brifingi üretir. API anahtarı yoksa aynı operasyon verisini tool fonksiyonlarından alıp deterministic demo brifingi döndürür.
