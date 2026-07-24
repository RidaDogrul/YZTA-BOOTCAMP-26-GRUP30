"""
OpenAPI / Swagger metadata — FS ekibi için merkezi dokümantasyon tanımları.

Swagger UI:  http://localhost:8000/docs
ReDoc:        http://localhost:8000/redoc
OpenAPI JSON: http://localhost:8000/openapi.json
"""
from typing import Any

API_DESCRIPTION = """
## Otonom Data Cleanroom & Tahminleme Ajanı — Backend API

Bu API, frontend (FS) ekibinin veri kaynağı bağlama, doğal dilde soru sorma
ve rapor görüntüleme ekranlarını geliştirmesi için hazırlanmıştır.

### Standart Yanıt Kuralları
| Durum | Format | Açıklama |
|-------|--------|----------|
| Başarı | İlgili `response_model` | 200/201 ile yapılandırılmış JSON |
| İstemci hatası | `{"detail": "..."}` | 400, 404 |
| Sunucu hatası | `{"detail": "..."}` | 500 — middleware tarafından yakalanır |

### Oturum Akışı (Frontend)
1. `POST /api/v1/connect-db/test` → bağlantıyı doğrula
2. `POST /api/v1/connect-db/connect` → `session_id` al
3. `POST /api/v1/chat/ask` → soru sor, yanıt al
4. `GET /api/v1/reports` → geçmiş raporları listele

### Not
Endpoint'ler şu an **şablon yanıt** döner. Gerçek iş mantığı Sprint 2–3'te eklenecektir.
"""

OPENAPI_TAGS: list[dict[str, Any]] = [
    {
        "name": "Health",
        "description": "API erişilebilirlik kontrolü. Kimlik doğrulama gerektirmez.",
    },
    {
        "name": "Connect DB",
        "description": (
            "PostgreSQL, MongoDB ve AWS S3 veri kaynaklarına bağlantı kurma, test etme "
            "ve şema keşfi. Ayarlar ekranı bu grubu kullanır."
        ),
    },
    {
        "name": "Chat",
        "description": (
            "Doğal dilde analiz/tahmin sorusu gönderme. Chat arayüzü bu grubu kullanır. "
            "Yanıt; özet, grafik datası ve aksiyon planını içerir."
        ),
    },
    {
        "name": "Reports",
        "description": (
            "Geçmiş raporları listeleme ve detay görüntüleme. "
            "Dashboard ana sayfası ve rapor detay ekranı bu grubu kullanır."
        ),
    },

    {
         "name": "Beta",
         "description": (
              "Kapalı beta davet kodları ve Design Partner erişim yönetimi. "
              "Admin işlemleri JWT role=admin claim'i gerektirir."
        ),
    },
]
