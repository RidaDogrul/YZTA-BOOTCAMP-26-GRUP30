# SmartFlow AI — Nihai Proje Dokümanı

**Proje Adı:** SmartFlow AI  
**Alt Başlık:** KOBİ ve Kooperatifler İçin Aksiyon Alan Yapay Zeka Operasyon Asistanı  
**Tema:** Yapay Zeka  
**Kapsam:** Case 1–5  
**Kapsam Dışı:** Case 6 — Analitik & İçgörü Üretimi  
**Proje Tipi:** Hackathon MVP / Çalışır Prototip  
**Hedef Süre:** 3 gün  
**Backend:** FastAPI & Python  
**AI Model:** Gemini API  
**Temel Yaklaşım:** Tek AI ajanı + tool/function calling + web chat + yönetici dashboard’u  

---

## 1. Proje Özeti

SmartFlow AI, küçük ve orta ölçekli işletmelerin, üretici kooperatiflerinin ve butik e-ticaret işletmelerinin müşteri iletişimi, sipariş takibi, kargo yönetimi, stok kontrolü ve günlük operasyon görevlerini tek bir yapay zeka destekli sistem üzerinden yönetmesini sağlayan web tabanlı bir operasyon asistanıdır.

Sistem müşteriden gelen doğal dildeki mesajları analiz eder, mesajın amacını belirler, ilgili sipariş, ürün, stok veya kargo verisine erişir ve müşteriye bağlama uygun bir cevap üretir. Aynı zamanda yönetici panelinde siparişlerin, kargo gecikmelerinin, kritik stokların ve günlük görevlerin sade bir özetini sunar.

SmartFlow AI klasik bir chatbot değildir. Chatbot sadece konuşur; SmartFlow AI müşteri mesajını işletmenin operasyon verileriyle ilişkilendirir, veri üzerinden karar verir, yöneticiye aksiyon önerir ve gerektiğinde dış servislerle bildirim akışı başlatır.

---

## 2. Tek Cümlelik Pitch

> SmartFlow AI, KOBİ’lerin müşteri mesajlarını anlayan, sipariş ve kargo durumunu kontrol eden, kritik stokları fark eden ve günlük operasyon görevlerini yapay zeka ile özetleyen aksiyon alan bir işletme operasyon asistanıdır.

---

## 3. Problem Tanımı

KOBİ’ler ve kooperatifler günlük operasyonlarını çoğunlukla manuel yöntemlerle yürütmektedir. Müşteri soruları WhatsApp, telefon, e-posta veya web kanalları üzerinden gelir. Sipariş bilgileri ayrı tablolarda, ürün ve stok bilgileri başka dosyalarda, kargo süreçleri ise farklı sistemlerde tutulur.

Bu yapı şu sorunlara yol açar:

- Müşterilerin “siparişim nerede?” sorularına manuel cevap verilmesi
- Sipariş durumunun farklı dosyalardan kontrol edilmesi
- Kargo gecikmelerinin müşteri şikayetinden sonra fark edilmesi
- Ürün stoklarının geç takip edilmesi
- Kritik stok durumunda tedarik aksiyonlarının gecikmesi
- Günlük operasyon görevlerinin kişiden kişiye değişmesi
- İşletme büyüdükçe manuel takibin sürdürülemez hale gelmesi

SmartFlow AI bu problemi, işletmenin temel operasyon akışlarını yapay zeka destekli bir sistemde birleştirerek çözer.

---

## 4. Hedef Kullanıcılar

### 4.1 KOBİ’ler

Günde 10–100 arası sipariş alan küçük ve orta ölçekli işletmeler.

Örnekler:

- Butik e-ticaret işletmeleri
- Instagram/WhatsApp üzerinden satış yapan küçük markalar
- Yerel ürün satan online işletmeler
- Fiziksel mağaza + online satış yapan karma işletmeler

### 4.2 Üretici Kooperatifleri

Tarım, gıda veya el sanatları alanında çalışan üretici grupları.

Örnekler:

- Kuru meyve üretici kooperatifleri
- Bal üreticileri
- Sabun, reçel, salça, zeytinyağı gibi yerel ürün satıcıları
- El yapımı ürün veya hediyelik eşya üreticileri

---

## 5. Kapsam Kararı

Bu proje, Yapay Zeka temasındaki ilk 5 case’i kapsar. Case 6, opsiyonel ve analitik/tahmin odaklı olduğu için MVP kapsamından çıkarılmıştır.

### 5.1 Kapsama Dahil Case’ler

| Case | Başlık | SmartFlow AI Karşılığı |
|---|---|---|
| Case 1 | Müşteri İletişiminin Otomasyonu | Müşteri mesajını AI ile anlar ve otomatik cevap üretir. |
| Case 2 | Ürün ve Sipariş Takibi | Sipariş ve ürün durumunu dashboard’da gösterir. |
| Case 3 | Kargo Süreçlerinin Yönetimi | Gecikmiş kargoyu tespit eder, müşteri ve yönetici bilgilendirmesi oluşturur. |
| Case 4 | Stok ve Envanter Yönetimi | Kritik stokları tespit eder, tedarikçi mail taslağı oluşturur. |
| Case 5 | İş Akışı ve Görev Yönetimi | Günlük operasyon brifingi ve görev listesi üretir. |

### 5.2 Kapsam Dışı

| Kapsam Dışı Özellik | Gerekçe |
|---|---|
| Case 6 — Analitik & İçgörü | Opsiyonel olduğu için MVP dışında bırakıldı. |
| Gelişmiş satış tahmin modeli | Veri ve modelleme yükü artırır. |
| Gerçek WhatsApp API | Token/webhook riski nedeniyle MVP’de web chat simülasyonu kullanılacak. |
| Gerçek kargo firması API | Erişim ve entegrasyon riski nedeniyle mock kargo verisi kullanılacak. |
| CrewAI/Multi-agent yapı | Tek ajan + tool use yeterli ve daha stabil. |
| Pinecone/ChromaDB | İlk MVP’de gerekli değil. |
| Gerçek ödeme/muhasebe entegrasyonu | Proje kapsamı dışında. |
| Rota optimizasyonu | Case 5 için sadece görev/brifing yapılacak, gerçek rota hesaplanmayacak. |
| React / Next.js | Frontend framework setup + state yönetimi zaman kaybı. Düz HTML + Tailwind CDN + Vanilla JS kullanılacak. |
| Conversation history (çok turlu bağlam) | Her müşteri mesajı bağımsız işlenecek. Multi-turn context yönetimi Gemini entegrasyonunu karmaşıklaştırır; hackathon demo'larında tek turlu mesajlar yeterlidir. |

---

## 6. Değer Önerisi

| Mevcut Durum | SmartFlow AI ile |
|---|---|
| Müşteri soruları manuel cevaplanır. | AI müşteri mesajını anlayıp otomatik cevap üretir. |
| Sipariş ve kargo bilgileri farklı yerlerden kontrol edilir. | Sipariş, ürün ve kargo durumu tek panelde görüntülenir. |
| Kargo gecikmeleri müşteri şikayet edince fark edilir. | Sistem gecikmeyi proaktif olarak gösterir. |
| Stok seviyesi manuel kontrol edilir. | Kritik stoklar dashboard’da uyarı olarak görünür. |
| Günlük iş dağılımı kişiden kişiye değişir. | AI günlük operasyon brifingi üretir. |
| İşletme sahibi operasyonu takip etmek için zaman kaybeder. | Tek panelden durum ve öncelikli aksiyonlar görülür. |

---

## 7. Case Bazlı Detaylı Çözüm

### 7.1 Case 1 — Müşteri İletişiminin Otomasyonu

**Amaç:** Müşteri mesajlarını doğal dilde anlayarak tekrar eden sorulara hızlı ve tutarlı cevap vermek.

**Kullanıcı senaryosu:**

```text
128 numaralı siparişim nerede?
```

**Sistem akışı:**

1. Mesaj FastAPI backend’e gelir.
2. AI ajanı mesajı analiz eder.
3. Intent `ORDER_STATUS` olarak belirlenir.
4. Mesajdan `order_id = 128` çıkarılır.
5. `get_order_status(order_id)` tool’u çağrılır.
6. Sipariş durumu ve kargo bilgisi alınır.
7. AI müşteriye doğal dilde cevap üretir.

**AI cevabı:**

```text
Merhaba, 128 numaralı siparişiniz kargoda görünüyor. Tahmini teslimat bugün 17:00’ye kadardır.
```

**Karşıladığı beklentiler:** doğal dil işleme, yapay zeka ajanı kullanımı, dinamik veriyle cevap üretimi, insan müdahalesini azaltma.

---

### 7.2 Case 2 — Ürün ve Sipariş Takibi

**Amaç:** Siparişlerin ve ürünlerin durumunu yönetici panelinde tek ekranda göstermek.

**Dashboard’da gösterilecek bilgiler:**

- Toplam sipariş sayısı
- Hazırlanıyor durumundaki siparişler
- Kargodaki siparişler
- Teslim edilen siparişler
- Gecikmiş siparişler
- Ürün stok durumu
- Son müşteri mesajları

**Yönetici paneli örneği:**

```text
Toplam Sipariş: 12
Hazırlanıyor: 5
Kargoda: 4
Teslim Edildi: 2
Gecikmiş: 1
Kritik Stok: 2 ürün
```

**Ürün bilgisi senaryosu:**

```text
Müşteri: Lavanta sabunu var mı?
AI: Evet, Lavanta Sabunu stokta mevcut. Şu anda 14 adet bulunmaktadır.
```

**Karşıladığı beklentiler:** ürün ve sipariş verilerinin işlenmesi, dinamik veri üzerinden anlamlı çıktı, kullanıcı deneyimi, gerçek kullanım senaryosuna uygunluk.

---

### 7.3 Case 3 — Kargo Süreçlerinin Yönetimi

**Amaç:** Kargo durumunu takip etmek, gecikmeleri tespit etmek ve müşteriye/yöneticiye bilgi vermek.

**Kullanıcı senaryosu:**

```text
142 numaralı siparişim neden gelmedi?
```

**Sistem verisi:**

```json
{
  "order_id": 142,
  "cargo_status": "Gecikmiş",
  "delay_days": 2,
  "estimated_delivery": "Yarın",
  "last_location": "Ankara Aktarma Merkezi"
}
```

**AI cevabı:**

```text
Merhaba, 142 numaralı siparişinizde kargo kaynaklı 2 günlük bir gecikme görünüyor. Bu durum için özür dileriz. Paketiniz şu anda Ankara Aktarma Merkezi’nde ve güncel tahmini teslimat yarın olarak görünmektedir.
```

**Dashboard uyarısı:**

```text
142 numaralı siparişte gecikme tespit edildi. Müşteri bilgilendirme mesajı hazırlandı.
```

**Opsiyonel harici aksiyon:**

Yöneticiye Resend API üzerinden e-posta uyarısı gönderilebilir:

```text
Konu: Kargo Gecikme Uyarısı — Sipariş #142
İçerik: 142 numaralı sipariş 2 gündür gecikmiş görünüyor. Müşteri mesaj taslağı dashboard’da onay bekliyor.
```

**Karşıladığı beklentiler:** aksiyon alabilen sistem, harici servis entegrasyonu, otomasyon seviyesi, müşteri şikayetinden önce işletmenin durumdan haberdar olması.

---

### 7.4 Case 4 — Stok ve Envanter Yönetimi

**Amaç:** Kritik stok seviyelerini tespit etmek ve yöneticiyi tedarik aksiyonu için hazırlamak.

**Basit iş kuralı:**

```text
Eğer stock_count <= critical_threshold ise ürün kritik stok olarak işaretlenir.
```

**Örnek veri:**

```json
{
  "product_id": "P002",
  "product_name": "Organik Zeytinyağı",
  "stock_count": 4,
  "critical_threshold": 5,
  "supplier_email": "tedarikci@example.com"
}
```

**AI uyarısı:**

```text
Organik Zeytinyağı stoğu kritik seviyeye düşmüş. Mevcut stok: 4 adet, kritik eşik: 5 adet.
```

**Tedarikçi mail taslağı:**

```text
Konu: Organik Zeytinyağı Stok Yenileme Talebi

Merhaba,

Organik Zeytinyağı ürünümüzün stoğu kritik seviyeye düşmüştür. En kısa sürede yeni tedarik için fiyat ve teslim süresi bilgisini paylaşabilir misiniz?

Teşekkürler.
```

**Önemli kapsam notu:** MVP’de AI doğrudan tedarikçiye mail göndermek zorunda değildir. Mail taslağını dashboard’da “Yönetici onayı bekliyor” olarak göstermek yeterlidir. İstenirse Resend API ile yöneticiye/takım mailine uyarı gönderilebilir.

**Karşıladığı beklentiler:** ürün verilerinin işlenmesi, aksiyon alabilen sistem, süreç otomasyonu, insan müdahalesini azaltma.

---

### 7.5 Case 5 — İş Akışı ve Görev Yönetimi

**Amaç:** Günlük operasyon için yöneticiye ve ekibe anlaşılır bir görev/brifing listesi sunmak.

**Kapsam sınırı:** Bu case için gerçek rota optimizasyonu yapılmayacaktır. Sistem yalnızca günlük sipariş, kargo ve stok durumlarını analiz ederek görev listesi oluşturacaktır.

**AI günlük brifing örneği:**

```text
Bugünkü Operasyon Özeti:

- Bugün toplam 12 aktif sipariş var.
- 5 sipariş hazırlanmayı bekliyor.
- 4 sipariş kargoda.
- 1 siparişte gecikme riski bulunuyor.
- 2 ürün kritik stok seviyesinde.
- Öncelikli görevler:
  1. #142 numaralı gecikmiş siparişin müşterisini bilgilendir.
  2. #128 ve #134 numaralı siparişleri paketle.
  3. Organik Zeytinyağı için tedarikçi mail taslağını kontrol et.
```

**Dashboard görev kartları:**

| Görev | Öncelik | Durum |
|---|---|---|
| #142 müşterisini bilgilendir | Yüksek | Bekliyor |
| #128 siparişini paketle | Orta | Bekliyor |
| Organik Zeytinyağı tedarik taslağını onayla | Yüksek | Onay bekliyor |

**Karşıladığı beklentiler:** iş akışı otomasyonu, süreçlerin mümkün olduğunca otomatik hale gelmesi, kullanıcı deneyimi, gerçek kullanım senaryosuna uygunluk.

---

## 8. Yapay Zeka Kullanım Stratejisi

SmartFlow AI’de yapay zeka dört ana iş için kullanılır:

### 8.1 Intent Classification

Müşteri mesajının amacını belirler.

| Intent | Örnek Mesaj |
|---|---|
| ORDER_STATUS | “128 numaralı siparişim nerede?” |
| PRODUCT_INFO | “Lavanta sabunu var mı?” |
| CARGO_STATUS | “Kargom gecikti mi?” |
| STOCK_ALERT | “Hangi ürünler kritik stokta?” |
| DAILY_BRIEFING | “Bugünkü durumu özetle.” |
| GENERAL | “Merhaba, bilgi alabilir miyim?” |

### 8.2 Entity Extraction

Mesajdan sipariş numarası, ürün adı veya müşteri bilgisi çıkarılır.

```json
{
  "message": "142 numaralı siparişim neden gelmedi?",
  "intent": "CARGO_STATUS",
  "entities": {
    "order_id": 142
  }
}
```

### 8.3 Tool Calling / Function Calling

AI doğrudan cevap uydurmaz. Önce ilgili tool’u çağırır, veri alır, sonra cevap üretir.

| Tool | Case | Görev |
|---|---|---|
| `get_order_status(order_id)` | Case 1–2 | Sipariş durumunu getirir. |
| `get_product_info(product_name)` | Case 2–4 | Ürün ve stok bilgisini getirir. |
| `get_cargo_status(order_id)` | Case 3 | Kargo durumunu getirir. |
| `check_stock_alerts()` | Case 4 | Kritik stokları listeler. |
| `draft_supplier_email(product_id)` | Case 4 | Tedarikçi mail taslağı üretir. |
| `generate_daily_briefing()` | Case 5 | Günlük operasyon görevlerini özetler. |
| `send_manager_alert(order_id)` | Case 3/4 | Yöneticiye e-posta/uyarı gönderir. |

### 8.4 Data-Aware Response Generation

AI, veritabanından gelen sonucu doğal dile çevirir.

Yanlış kullanım:

```text
AI tahmin ederek “Siparişiniz yarın gelir” der.
```

Doğru kullanım:

```text
AI önce sipariş ve kargo verisini çeker, sonra “Tahmini teslimat yarın” der.
```

---

## 9. RAG Benzeri Veri Etkileşimi Açıklaması

Proje için ayrıca ChromaDB/Pinecone gibi bir vektör veritabanı kullanmak zorunlu değildir. Çünkü bu MVP’de veriler çoğunlukla yapısaldır:

- Sipariş ID
- Ürün adı
- Kargo durumu
- Stok miktarı
- Görev durumu

Bu yüzden retrieval işlemi function calling ve SQL/JSON sorguları ile yapılacaktır.

**Klasik RAG:**

```text
Soru → ilgili doküman parçasını bul → LLM’e bağlam olarak ver → cevap üret
```

**SmartFlow AI:**

```text
Soru → ilgili tool’u seç → DB/JSON’dan doğru kaydı getir → LLM’e bağlam olarak ver → cevap üret
```

Bu nedenle SmartFlow AI, yapısal operasyon verileri için RAG benzeri bir veriyle etkileşim yaklaşımı kullanır. Vektör arama yerine daha doğru ve güvenilir olan yapısal sorgulama tercih edilir.

---

## 10. Teknik Mimari

### 10.1 Yüksek Seviyeli Mimari

```text
Müşteri Web Chat
       ↓
FastAPI Backend
       ↓
Gemini AI Agent
       ↓
Tool Functions
 ┌─────┼────────────┬──────────────┬─────────────┐
 ↓     ↓            ↓              ↓             ↓
Orders Products   Cargo/Shipment  Tasks       Messages
Data   Data       Data            Data        Data
       ↓
AI Response Generator
       ↓
Müşteri Cevabı + Dashboard Güncellemesi + Yönetici Aksiyonu
```

### 10.2 Teknoloji Yığını

| Katman | Teknoloji | Gerekçe |
|---|---|---|
| Backend | FastAPI | Kurallara uygun, hızlı API geliştirme |
| Programlama Dili | Python | AI entegrasyonları için uygun |
| AI Model | Gemini API | Hackathon önerisi, hızlı cevap, function calling desteği |
| Veri | SQLite veya JSON seed data | MVP için hızlı ve stabil |
| ORM | SQLAlchemy | Temiz modelleme ve sorgulama |
| Validation | Pydantic | FastAPI ile uyumlu |
| Frontend | HTML + Tailwind CDN + Vanilla JS | React/Next.js kullanılmıyor — framework setup zaman kaybı |
| Harici Servis | Resend API | E-posta uyarısı için |
| Kod Paylaşımı | GitHub | Dokümantasyon ve teslim |

### 10.3 Neden Tek Ajan?

Multi-agent mimarisi teorik olarak güçlüdür ancak MVP için gereksiz karmaşıklık yaratır. Bu projede tek merkezi AI ajanı kullanılır. Ajan, kullanıcının mesajına göre doğru tool’u seçer.

Tek ajan yeterlidir çünkü:

- Case sayısı sınırlıdır.
- Görevler net ayrılmıştır.
- Tool’lar işlevsel olarak bağımsızdır.
- Demo stabilitesi daha önemlidir.
- Kod kalitesi ve çalışabilirlik artar.

---

## 11. Veri Modeli

### 11.1 Orders Tablosu

| Alan | Tip | Açıklama |
|---|---|---|
| order_id | integer | Sipariş numarası |
| customer_name | string | Müşteri adı |
| customer_phone | string | Müşteri telefonu |
| product_id | string | Ürün ID |
| quantity | integer | Adet |
| status | string | Hazırlanıyor / Kargoda / Teslim Edildi |
| cargo_status | string | Zamanında / Gecikmiş / Dağıtımda |
| estimated_delivery | string/date | Tahmini teslimat |
| created_at | datetime | Sipariş tarihi |

### 11.2 Products Tablosu

| Alan | Tip | Açıklama |
|---|---|---|
| product_id | string | Ürün ID |
| product_name | string | Ürün adı |
| stock_count | integer | Mevcut stok |
| critical_threshold | integer | Kritik stok eşiği |
| supplier_email | string | Tedarikçi e-postası |
| price | float | Ürün fiyatı |
| available | boolean | Stokta var mı? |

### 11.3 Shipments Tablosu

| Alan | Tip | Açıklama |
|---|---|---|
| shipment_id | integer | Kargo ID |
| order_id | integer | Sipariş ID |
| carrier | string | Kargo firması |
| tracking_number | string | Takip numarası |
| actual_status | string | Yolda / Dağıtımda / Teslim Edildi / Gecikmiş |
| last_location | string | Son kargo konumu |
| delay_days | integer | Gecikme günü |
| estimated_delivery | string/date | Tahmini teslimat |

### 11.4 Tasks Tablosu

| Alan | Tip | Açıklama |
|---|---|---|
| task_id | integer | Görev ID |
| task_type | string | Paketleme / Kargo / Stok / Müşteri Bilgilendirme |
| description | text | Görev açıklaması |
| priority | string | Yüksek / Orta / Düşük |
| status | string | Bekliyor / Tamamlandı / Onay bekliyor |
| related_order_id | integer | İlgili sipariş |
| related_product_id | string | İlgili ürün |

### 11.5 Messages Tablosu

| Alan | Tip | Açıklama |
|---|---|---|
| message_id | integer | Mesaj ID |
| customer_message | text | Müşteri mesajı |
| ai_response | text | AI cevabı |
| intent | string | Bulunan intent |
| status | string | Gönderildi / Onay bekliyor |
| created_at | datetime | Oluşturma zamanı |

---

## 12. API Tasarımı

### 12.1 Ana Endpointler

| Method | Endpoint | Açıklama |
|---|---|---|
| POST | `/api/chat` | Müşteri mesajını analiz eder ve cevap üretir. |
| GET | `/api/orders` | Siparişleri listeler. |
| GET | `/api/orders/{order_id}` | Tek sipariş detayı getirir. |
| GET | `/api/products` | Ürünleri listeler. |
| GET | `/api/shipments` | Kargo durumlarını listeler. |
| GET | `/api/dashboard/summary` | Yönetici paneli özetini getirir. |
| GET | `/api/tasks` | Günlük görevleri listeler. |
| POST | `/api/tasks/generate` | AI günlük görev/brifing üretir. (**Bir kez çağrılır, sonuç cache'lenir. Her dashboard yüklenişinde Gemini çağırmak latency ve maliyet riski yaratır.**) |
| POST | `/api/alerts/send` | Yöneticiye e-posta uyarısı gönderir. |
| POST | `/api/seed` | Demo verisini sıfırlar. |
| GET | `/health` | Sağlık kontrolü yapar. |

### 12.2 POST /api/chat

**Request:**

```json
{
  "message": "142 numaralı siparişim neden gelmedi?"
}
```

**Response:**

```json
{
  "intent": "CARGO_STATUS",
  "entities": {
    "order_id": 142
  },
  "reply": "142 numaralı siparişinizde 2 günlük kargo gecikmesi görünüyor. Bu durum için özür dileriz. Güncel tahmini teslimat yarın olarak görünmektedir.",
  "tool_calls": [
    "get_order_status",
    "get_cargo_status"
  ],
  "dashboard_note": "142 numaralı sipariş için gecikme uyarısı oluşturuldu."
}
```

### 12.3 GET /api/dashboard/summary

```json
{
  "total_orders": 12,
  "preparing_orders": 5,
  "in_cargo_orders": 4,
  "delivered_orders": 2,
  "delayed_orders": 1,
  "critical_stock_products": 2,
  "pending_tasks": 4,
  "ai_summary": "Bugün 12 sipariş var. 5 sipariş hazırlanmalı, 1 kargo gecikmiş, 2 ürün kritik stokta."
}
```

---

## 13. Kullanıcı Arayüzü

### 13.1 Ana Ekran Yapısı

Demo için tek sayfalık bir arayüz önerilir.

```text
Sol taraf: Müşteri Chat Simülasyonu
Sağ taraf: Yönetici Dashboard’u
Alt bölüm: AI Günlük Brifing + Görevler
```

Bu düzen sayesinde jüri hem müşteri deneyimini hem işletme panelini aynı anda görür.

### 13.2 Chat Alanı

Özellikler:

- Mesaj yazma alanı
- Gönder butonu
- AI cevabı
- Intent etiketi
- Kullanılan tool listesi
- Typing indicator
- Hızlı demo butonları

Hızlı butonlar:

```text
🔍 Siparişim nerede?
📦 Kargom gecikti mi?
🧴 Lavanta sabunu var mı?
🧾 Bugünkü durumu özetle
```

### 13.3 Dashboard Kartları

Dashboard’da şu kartlar bulunur:

- Toplam Sipariş
- Hazırlanıyor
- Kargoda
- Teslim Edildi
- Gecikmiş
- Kritik Stok
- Onay Bekleyen Aksiyonlar
- Günlük Görevler

### 13.4 Durum Rozetleri

| Durum | Renk |
|---|---|
| Teslim Edildi | Yeşil |
| Kargoda | Mavi |
| Hazırlanıyor | Sarı |
| Gecikmiş | Kırmızı |
| Kritik Stok | Turuncu |
| Onay Bekliyor | Mor |

---

## 14. 3 Günlük Geliştirme Planı

### Gün 1 — Backend, Veri ve Temel Tool’lar

- FastAPI proje iskeleti kurulur.
- Veri modeli hazırlanır.
- Seed data oluşturulur.
- Orders, Products, Shipments, Tasks, Messages tabloları hazırlanır.
- `get_order_status`, `get_product_info`, `get_cargo_status` tool’ları yazılır.
- `/api/chat` endpointinin ilk versiyonu oluşturulur.

**Gün sonu çıktısı:** Backend çalışır, demo verisi yüklenir, sipariş ve ürün verisi API’den okunur, basit chat cevabı döner.

### Gün 2 — AI Agent, Stok ve Kargo Aksiyonu

- Gemini API entegrasyonu yapılır.
- Intent classification eklenir.
- Entity extraction eklenir.
- Function calling/tool dispatch döngüsü kurulur.
- Kritik stok kuralı yazılır.
- Kargo gecikmesi tespit edilir.
- Tedarikçi mail taslağı oluşturma fonksiyonu yazılır.
- Yönetici e-posta uyarısı için Resend API entegrasyonu yapılır.

**Gün sonu çıktısı:** Müşteri mesajları AI ile analiz edilir, sipariş/ürün/kargo tool’ları çalışır, kritik stok ve kargo gecikmesi dashboard’a düşer.

### Gün 3 — Frontend, Demo ve Dokümantasyon

- Chat ekranı yapılır.
- Yönetici dashboard’u yapılır.
- AI günlük brifing/görev listesi eklenir.
- Hızlı demo butonları eklenir.
- UI sadeleştirilir.
- README hazırlanır.
- Mimari diyagram eklenir.
- Demo script yazılır.
- Ekran kaydı alınır.
- GitHub repo düzenlenir.

**Gün sonu çıktısı:** Çalışır prototip, kısa demo, README, GitHub repo, mimari açıklama, demo videosu veya canlı demo.

---

## 15. Demo Akışı

**Demo süresi:** 5–7 dakika

### 15.1 Açılış

```text
SmartFlow AI, KOBİ’lerin müşteri mesajı, sipariş, kargo, stok ve günlük operasyon takibini yapay zeka ile otomatikleştiren bir web uygulamasıdır.
```

### 15.2 Demo 1 — Sipariş Sorgulama

```text
Müşteri: 128 numaralı siparişim nerede?
AI: 128 numaralı siparişiniz kargoda görünüyor. Tahmini teslimat bugün 17:00’ye kadardır.
```

### 15.3 Demo 2 — Kargo Gecikmesi

```text
Müşteri: 142 numaralı siparişim neden gelmedi?
AI: 142 numaralı siparişinizde 2 günlük kargo gecikmesi görünüyor. Bu durum için özür dileriz.
Dashboard: Kargo Gecikme Uyarısı — #142
```

### 15.4 Demo 3 — Ürün/Stok Sorgusu

```text
Müşteri: Organik zeytinyağı var mı?
AI: Evet, Organik Zeytinyağı stokta mevcut. Ancak stok 4 adede düştüğü için kritik seviyede görünüyor.
Dashboard: Kritik Stok — Organik Zeytinyağı, 4 adet
```

### 15.5 Demo 4 — Tedarikçi Mail Taslağı

```text
AI: Organik Zeytinyağı için tedarikçiye gönderilecek stok yenileme mail taslağı hazırlandı.
```

### 15.6 Demo 5 — Günlük Operasyon Brifingi

```text
Bugün 12 sipariş var. 5 sipariş hazırlanmayı bekliyor. 1 kargo gecikmiş. 2 ürün kritik stokta. Öncelikli görevler: #142 müşterisini bilgilendir, #128 ve #134 siparişlerini paketle, Organik Zeytinyağı tedarik taslağını kontrol et.
```

---

## 16. Değerlendirme Kriterlerine Göre Uyum

### 16.1 Problem Tanımı & Değer Önerisi

Karşılıyor. Problem net: KOBİ’lerin müşteri, sipariş, kargo ve stok süreçlerini manuel yönetmesi. Değer: AI bu süreçleri daha hızlı, izlenebilir ve otomatik hale getirir.

### 16.2 Yapay Zeka Kullanımının Doğruluğu

Karşılıyor. AI doğru yerde kullanılır: doğal dil anlama, intent classification, entity extraction, tool calling, veriyle cevap üretme ve günlük brifing oluşturma.

### 16.3 Teknik Uygulama & Mimari

Karşılıyor. FastAPI + Python, Gemini API, SQLAlchemy/SQLite, Pydantic, tool-based AI agent, dashboard + chat arayüzü ve Resend API kullanılacaktır.

### 16.4 Ürünleşme & Kullanıcı Deneyimi

Karşılıyor. Tek sayfalık sade arayüz, chat + dashboard, durum rozetleri, hızlı butonlar ve yönetici aksiyon kartları bulunur.

### 16.5 Yenilikçilik

Karşılıyor. Proje klasik chatbot değildir. Veriyle konuşan ve aksiyon öneren AI operasyon asistanıdır.

### 16.6 Çalışabilirlik

Karşılıyor. Kapsam kontrollü tutulmuştur. Gerçek API bağımlılıkları minimumdur. Mock veri ve seed data ile stabil demo yapılabilir.

### 16.7 Sunum

Karşılıyor. 5–7 dakikalık net demo akışı vardır.

### 16.8 Dokümantasyon & Kod Paylaşımı

Karşılıyor. README, API dokümanı, mimari açıklama, demo script ve GitHub repo hazırlanacaktır.

---

## 17. Riskler ve Önlemler

| Risk | Etki | Önlem |
|---|---|---|
| Kapsamın büyümesi | Proje yetişmeyebilir | Case 6 çıkarıldı, rota optimizasyonu yapılmayacak. |
| Gemini API hatası | Demo aksayabilir | Seed cevap/mock fallback hazırlanacak. |
| Resend e-posta gecikmesi | Demo etkisi düşebilir | E-posta opsiyonel gösterilecek, dashboard taslağı yedek olacak. |
| AI yanlış cevap üretmesi | Güven düşer | Tool kullanmadan cevap vermesi engellenecek. |
| UI karmaşıklaşması | UX düşer | Tek sayfa dashboard yapılacak. |
| Gerçek API entegrasyonu yetişmemesi | Teknik risk | WhatsApp/kargo gerçek API kullanılmayacak. |
| Case 5’in büyümesi | Zaman kaybı | Sadece brifing ve görev listesi yapılacak. |

---

## 18. GitHub README İçeriği

README’de şu başlıklar bulunmalıdır:

1. Proje adı
2. Problem tanımı
3. Çözüm özeti
4. Kapsanan case’ler
5. Kapsam dışı bırakılanlar
6. Yapay zeka yaklaşımı
7. Sistem mimarisi
8. Veri modeli
9. API endpointleri
10. Kurulum adımları
11. Demo senaryosu
12. Kullanılan teknolojiler
13. Takım görev dağılımı
14. Future work

---

## 19. Önerilen Dosya Yapısı

```text
smartflow-ai/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── seed.py
│   │   ├── ai_service.py
│   │   ├── tools.py
│   │   ├── dashboard_service.py
│   │   └── email_service.py
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── chat.html          # Müşteri chat arayüzü (HTML + Tailwind CDN + Vanilla JS)
│   └── dashboard.html     # Yönetici paneli (HTML + Tailwind CDN + Vanilla JS)
│   # NOT: React/Next.js kullanılmıyor. 3 günlük hackathon'da
│   # framework setup + state management zaman kaybıdır.
│   # Tailwind CDN + Vanilla JS ile chat ve dashboard 3-4 saatte biter.
│
├── docs/
│   ├── architecture.md
│   ├── api-design.md
│   ├── demo-script.md
│   └── data-model.md
│
├── README.md
└── demo-video-link.txt
```

---

## 20. Future Work

MVP sonrası eklenecek özellikler:

- Case 6 — Analitik ve içgörü üretimi
- Satış tahmini
- Haftalık stok ihtiyacı tahmini
- Gerçek WhatsApp Business API
- Gerçek kargo firması API
- Gelişmiş RAG bilgi tabanı
- Çoklu işletme desteği
- Kullanıcı yetkilendirme
- Mobil uygulama
- Detaylı raporlama

---

## 21. Jüriye Verilecek Kısa Cevaplar

### Bu proje hangi problemi çözüyor?

KOBİ’lerin müşteri mesajı, sipariş, kargo, stok ve günlük görev takibini manuel yapma problemini çözüyor.

### Yapay zeka nerede kullanılıyor?

AI müşteri mesajını anlıyor, sipariş numarası veya ürün adını çıkarıyor, ilgili tool’u çağırıyor, veriye göre cevap üretiyor ve günlük operasyon brifingi oluşturuyor.

### Bu sadece chatbot mu?

Hayır. Chatbot sadece konuşur. SmartFlow AI işletmenin sipariş, kargo, stok ve görev verileriyle etkileşime geçer; aksiyon önerir ve yönetici dashboard’unu günceller.

### Case 6 neden yok?

Case 6 opsiyonel ve analitik/tahmin odaklı olduğu için MVP kapsamından çıkarılmıştır. Böylece çalışan ve stabil bir ürün çıkarmaya odaklanılmıştır.

### Harici servis var mı?

Evet. Yöneticiye bildirim göndermek için Resend API kullanılabilir. Ayrıca sistem mimarisi WhatsApp ve gerçek kargo API entegrasyonlarına açık tasarlanmıştır.

### Neden FastAPI?

FastAPI, Python tabanlı olduğu için AI servisleriyle hızlı entegre olur ve hackathon teknik beklentilerine uygundur.

---

## 22. Son Proje Tanımı

SmartFlow AI, KOBİ’ler ve üretici kooperatifleri için geliştirilen FastAPI tabanlı bir yapay zeka operasyon asistanıdır. Sistem müşteri mesajlarını Gemini destekli AI ajanı ile analiz eder; sipariş, ürün, kargo ve stok verilerini tool/function calling yaklaşımıyla sorgular; müşteriye doğru ve bağlama uygun cevaplar üretir. Yönetici panelinde ise sipariş durumu, kargo gecikmeleri, kritik stoklar ve günlük görevler sade bir arayüzle gösterilir.

MVP kapsamında Case 1–5 karşılanır:

1. Müşteri iletişiminin otomasyonu
2. Ürün ve sipariş takibi
3. Kargo süreçlerinin yönetimi
4. Stok ve envanter yönetimi
5. İş akışı ve görev yönetimi

Case 6, opsiyonel olduğu için future work olarak bırakılmıştır.

SmartFlow AI’nın temel stratejisi, çok fazla özelliği yüzeysel yapmak yerine, hackathon kriterlerini karşılayan çalışır, anlaşılır ve demo edilebilir bir operasyon asistanı üretmektir.
