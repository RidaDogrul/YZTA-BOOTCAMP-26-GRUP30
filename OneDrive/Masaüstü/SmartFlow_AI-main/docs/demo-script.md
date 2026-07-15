# SmartFlow AI Demo Script

Demo süresi: 5-7 dakika.

## 1. Açılış

SmartFlow AI, KOBİ'lerin müşteri mesajı, sipariş, kargo, stok ve günlük operasyon takibini yapay zeka ile otomatikleştiren bir web uygulamasıdır.

## 2. Sipariş Sorgulama

Müşteri chat ekranında:

```text
128 numaralı siparişim nerede?
```

Beklenen sonuç: AI sipariş durumunu ve tahmini teslimatı veriyle cevaplar; `get_order_status` tool çağrısı görünür.

## 3. Kargo Gecikmesi

Müşteri chat ekranında:

```text
142 numaralı siparişim neden gelmedi?
```

Beklenen sonuç: AI gecikme gününü, son konumu ve tahmini teslimatı açıklar; dashboard notu oluşur.

## 4. Ürün ve Kritik Stok

Müşteri chat ekranında:

```text
Organik zeytinyağı var mı?
```

Beklenen sonuç: AI stok adedini ve kritik stok durumunu söyler. Dashboard'da kritik stok kartı ve tedarikçi mail taslağı gösterilir.

## 5. Günlük Operasyon Brifingi

Dashboard'da AI Günlük Brifing bölümünde yenile butonuna basılır ya da endpoint çağrılır:

```text
POST /api/tasks/generate
```

Beklenen sonuç: toplam sipariş, hazırlanacak siparişler, gecikmiş kargo, kritik stok ve öncelikli görevler kısa bir yönetici brifingi olarak görünür.

## 6. Kapanış

Jüriye vurgulanacak cümle:

```text
SmartFlow AI klasik bir chatbot değil; işletmenin operasyon verisini tool/function calling ile sorgulayan ve yönetici aksiyonu üreten bir yapay zeka asistanıdır.
```
