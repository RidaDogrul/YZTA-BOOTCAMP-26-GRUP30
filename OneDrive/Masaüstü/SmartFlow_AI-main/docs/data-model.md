# SmartFlow AI Veri Modeli

## Products

| Alan | Tip | Açıklama |
|---|---|---|
| `product_id` | string | Ürün ID |
| `product_name` | string | Ürün adı |
| `stock_count` | integer | Mevcut stok |
| `critical_threshold` | integer | Kritik stok eşiği |
| `supplier_email` | string | Tedarikçi e-postası |
| `price` | float | Ürün fiyatı |
| `available` | boolean | Stokta var mı? |

## Orders

| Alan | Tip | Açıklama |
|---|---|---|
| `order_id` | integer | Sipariş numarası |
| `customer_name` | string | Müşteri adı |
| `customer_phone` | string | Müşteri telefonu |
| `product_id` | string | Ürün ilişkisi |
| `quantity` | integer | Adet |
| `status` | string | Hazırlanıyor / Kargoda / Teslim Edildi |
| `cargo_status` | string | Zamanında / Gecikmiş / Dağıtımda |
| `estimated_delivery` | string | Tahmini teslimat |
| `created_at` | datetime | Oluşturma zamanı |

## Shipments

| Alan | Tip | Açıklama |
|---|---|---|
| `shipment_id` | integer | Kargo kayıt ID |
| `order_id` | integer | Sipariş ilişkisi |
| `carrier` | string | Kargo firması |
| `tracking_number` | string | Takip numarası |
| `actual_status` | string | Fiili kargo durumu |
| `last_location` | string | Son konum |
| `delay_days` | integer | Gecikme günü |
| `estimated_delivery` | string | Tahmini teslimat |

## Tasks

| Alan | Tip | Açıklama |
|---|---|---|
| `task_id` | integer | Görev ID |
| `task_type` | string | Paketleme / Kargo / Stok / Müşteri Bilgilendirme |
| `description` | text | Görev açıklaması |
| `priority` | string | Yüksek / Orta / Düşük |
| `status` | string | Bekliyor / Tamamlandı / Onay bekliyor |
| `related_order_id` | integer | İlgili sipariş |
| `related_product_id` | string | İlgili ürün |

## Messages

| Alan | Tip | Açıklama |
|---|---|---|
| `message_id` | integer | Mesaj ID |
| `customer_message` | text | Müşteri mesajı |
| `ai_response` | text | AI cevabı |
| `intent` | string | Bulunan intent |
| `status` | string | Gönderildi / Onay bekliyor |
| `created_at` | datetime | Oluşturma zamanı |
