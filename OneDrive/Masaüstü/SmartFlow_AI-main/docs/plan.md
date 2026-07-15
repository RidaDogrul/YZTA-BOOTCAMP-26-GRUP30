Kişi 1 — Backend Altyapı & Veri Katmanı

config.py — ortam değişkenleri
database.py — SQLite engine, session yönetimi
models.py — SQLAlchemy ORM modelleri (Orders, Products, Shipments, Tasks, Messages)
schemas.py — Pydantic modelleri (ilk 2 saatte yaz, herkese paylaş)
seed.py — demo verisi
crud.py — DB helper fonksiyonları (Kişi 2'ye verilecek)
dashboard_service.py — dashboard özet hesaplama servisi
main.py — uygulama iskeleti, router kayıtları, CORS, startup
GET /api/orders, GET /api/orders/{order_id}
GET /api/products
GET /api/shipments
GET /api/tasks
GET /api/dashboard/summary
POST /api/seed
GET /health


Kişi 2 — AI Servis, Gemini Entegrasyonu & Tool Calling

ai_service.py — Gemini API bağlantısı, chat oturumu, tool calling dispatch döngüsü
tools.py — tüm tool fonksiyonları (önce mock, sonra Kişi 1'in crud.py'siyle swap)
email_service.py — Resend API entegrasyonu
Gemini function declaration'larının yazılması (7 tool için)
Intent classification & entity extraction mantığı
POST /api/chat
POST /api/tasks/generate
POST /api/alerts/send


Kişi 3 — Müşteri Chat Arayüzü

frontend/chat.html — tek dosya (HTML + Tailwind CDN + Vanilla JS)
Chat balonu render (kullanıcı / AI ayrımı)
Intent badge gösterimi
Kullanılan tool listesi gösterimi
Typing indicator (3 nokta animasyonu)
Hızlı demo butonları (5 adet, proje dokümanındaki senaryolar)
POST /api/chat entegrasyonu


Kişi 4 — Yönetici Dashboard Arayüzü

frontend/dashboard.html — tek dosya (HTML + Tailwind CDN + Vanilla JS)
Özet stat kartları (Toplam, Hazırlanıyor, Kargoda, Teslim, Gecikmiş, Kritik Stok)
Durum rozetleri (yeşil, mavi, sarı, kırmızı, turuncu, mor)
Görev kartları tablosu (öncelik + durum gösterimi)
Gecikmiş sipariş uyarı bölümü
Kritik stok uyarı bölümü
Tedarikçi mail taslağı modal görünümü
AI günlük brifing bölümü + yenile butonu
Yönetici uyarısı gönder butonu (POST /api/alerts/send)
GET /api/dashboard/summary, GET /api/tasks, GET /api/orders, GET /api/products, GET /api/shipments entegrasyonları