# YZTA-BOOTCAMP-26-GRUP30

# Information About Team and Product

## Team Members

| Photo | Name | Title | Socials Media |
|---|---|---|---|
|  | Elif Keskin | Scrum Master | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/elif-keskin-data-professional/) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/elifkeskin) |
|  | Recep Atabey Demir | Product Owner | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/recep-atabey-demir/) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/Atabeydem) |
|  | Rida Doğrul | Developer | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/rida-doğrul/) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/RidaDogrul) |
|  | Nimet Asude Yalçın | Developer | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/nimet-asude-yalçın) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/asudeyal) |
|  | Sevde Koç | Developer | [![LinkedIn](https://img.shields.io/badge/-LinkedIn-0077B5?style=flat&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/sevde-ko%C3%A7-5b335b26b/) [![GitHub](https://img.shields.io/badge/-GitHub-181717?style=flat&logo=github&logoColor=white)](https://github.com/svdsevde-cpu) |






# Otonom Data Cleanroom ve Tahminleme Ajanı

Şirketlerin dağınık veri tabanlarına (SQL, NoSQL, Cloud) bağlanan; ham veriyi temizleyen, eksikleri tamamlayan ve kullanıcı hiçbir teknik kod yazmadan doğal dilde soru sorduğunda arka planda makine öğrenmesi modellerini çalıştırıp tahmini raporlar ve aksiyon planları üreten otonom bir AI ajanı.

---

## Proje Yapısı

```
ai-data-agent/
│
├── src/
│   ├── api/                        # API Katmanı (FastAPI)
│   │   ├── v1/
│   │   │   ├── endpoints/          # chat, connect_db, reports route'ları
│   │   │   └── api.py
│   │   └── middleware/             # Güvenlik ve Kimlik Doğrulama
│   │
│   ├── connectors/                 # Veri Tabanı Bağlantıları
│   │   ├── postgres.py             # SQL bağlantı ve şema okuma logiği
│   │   ├── mysql.py
│   │   └── s3_storage.py          # Dosya/Bulut depolama bağlantıları
│   │
│   ├── security/                   # Cleanroom ve Maskeleme
│   │   └── anonymizer.py           # PII (Kişisel veri) filtreleme algoritmaları
│   │
│   ├── agents/                     # Yapay Zeka Ajanları (CrewAI / LangChain)
│   │   ├── orchestrator.py         # Ajanlar arası iş akışını yöneten beyin
│   │   ├── prompts.py              # System prompt'ları ve text-to-sql şablonları
│   │   └── tools/                  # Ajanların kullanabileceği Python fonksiyonları
│   │
│   ├── ml_models/                  # Tahminleme Motoru (AutoML)
│   │   ├── forecaster.py           # Zaman serisi (Prophet/LightGBM) tahmin logiği
│   │   └── preprocessor.py         # Eksik veri tamamlama ve outlier temizliği
│   │
│   └── utils/                      # Yardımcı Fonksiyonlar (Logger, Formatters)
│       ├── config.py               # .env tabanlı merkezi ayar yönetimi
│       └── logger.py               # JSON logging ve request-id takibi
│
├── tests/                          # Birim ve Entegrasyon Testleri
├── requirements.txt                # Bağımlılıklar (fastapi, pandas, crewai, scikit-learn)
└── main.py                         # Uygulamanın ayağa kalktığı ana dosya
```

---

## Veri Akış Şeması (Data & Logic Flow)

Kullanıcının doğal dilde yazdığı bir sorunun arka planda nasıl işlendiğini gösteren uçtan uca pipeline:

```
[KULLANICI] ──(1. Doğal Dil Sorusu)──> [FRONTEND / CHAT UI]
                                                │
                                                ▼
                                    [BACKEND: API GATEWAY]
                                                │
                             (2. Şema Entegrasyonu & Güvenlik Filtresi)
                                                │
                                                ▼
                           [AI AGENT ORCHESTRATOR] (CrewAI / LangChain)
                                                │
                  ┌─────────────────────────────┴─────────────────────────────┐
                  ▼                                                           ▼
       [AGENT 1: SQL/DATA EXECUTOR]                             [AGENT 2: DATA SCIENTIST]
        - Şemaya göre SQL üretir                                 - Pandas ile temizlik yapar
        - DB'den ham veriyi çeker                                - Eksik verileri tamamlar
        - Veriyi Sandbox'a aktarır                               - ML Tahmin modelini tetikler
                  │                                                           │
                  └─────────────────────────────┬─────────────────────────────┘
                                                │
                                   (3. Temizlenmiş & Tahminlenmiş Veri)
                                                │
                                                ▼
                                    [AGENT 3: INSIGHT GENERATOR]
                                     - Sonuçları JSON/Metin yapar
                                     - Grafik datası (D3.js) hazırlar
                                     - Aksiyon planı üretir
                                                │
                                                ▼
[KULLANICI] <──(4. Rapor, Grafikler & Aksiyon Planı)── [FRONTEND]
```

---

## Geliştirme Aşamaları

### Aşama 1 — Altyapı ve Veri Bağlantıları

| Görev | Açıklama |
|-------|----------|
| **1.1 Veri Kaynağı Konnektörleri** | PostgreSQL, MySQL, MongoDB ve AWS S3/Snowflake için güvenli bağlantı arayüzleri |
| **1.2 Veri Keşif & Şema Çıkarma** | Tablo şemalarını otomatik tespit eden ve LLM'e uygun JSON Meta-Data formatına çeviren motor |
| **1.3 Veri Güvenliği & Maskeleme** | KVKK/GDPR kapsamındaki PII verilerini (isim, e-posta, telefon) ajana göndermeden önce yerelde anonimleştiren filtre katmanı |

### Aşama 2 — Otonom AI Ajan Zekası

| Görev | Açıklama |
|-------|----------|
| **2.1 Otonom Veri Temizleme** | Null değerleri ortalama/medyan/interpolasyon ile dolduran ve outlier'ları tespit edip işaretleyen pipeline |
| **2.2 Text-to-SQL / Text-to-Python** | Kullanıcı sorusunu veritabanı şemasına bakarak doğru SQL sorgusuna çeviren LangChain/LlamaIndex prompt zinciri |
| **2.3 AutoML Entegrasyonu** | Prophet, ARIMA veya LightGBM ile zaman serisi tahminleri çalıştıran ve en doğru modeli seçen Python modülü |

### Aşama 3 — Raporlama ve Arayüz

| Görev | Açıklama |
|-------|----------|
| **3.1 Doğal Dilde Raporlama** | Tahmin sonuçlarını anlaşılır Türkçe/İngilizce rapora çeviren LLM özet katmanı + Chart.js/D3.js grafikleri |
| **3.2 Aksiyon Planı Üretici** | Sorunu tespit etmekle kalmayan, çözüm önerileri de üreten reasoning adımı |
| **3.3 No-Code Dashboard** | Veri kaynaklarını bağlamak için ayarlar ekranı, ajan ile konuşmak için chat arayüzü ve raporların listelendiği ana sayfa |

### Aşama 4 — İş Geliştirme ve Pazara Giriş

| Görev | Açıklama |
|-------|----------|
| **4.1 Kapalı Beta** | E-ticaret / perakende sektöründen 2-3 Design Partner ile anonimleştirilmiş gerçek veri testi |
| **4.2 Fiyatlandırma** | Veri boyutu ve kullanım saatine dayalı katmanlı SaaS modeli (Freemium / Growth / Enterprise) |

---

## Örnek API Çıktısı

```json
{
  "status": "success",
  "summary": "Önümüzdeki ay Tekstil kategorisinde %12 ciro kaybı riski tespit edilmiştir.",
  "chart_data": [
    {"date": "2026-07-01", "predicted_sales": 12000}
  ],
  "action_plan": [
    "Tekstil kategorisinde acil indirim kampanyası planlayın.",
    "Tedarik siparişlerini %10 kısın."
  ]
}
```

---

## Sprint Planı — Rol ve Görev Dağılımı (6 Hafta)

| Rol | Sorumlu Olduğu Görevler | Haftalık Çıktı |
|-----|------------------------|----------------|
| **Veri Mühendisi** | DB konnektörleri, KVKK maskeleme, veri temizleme pipeline'ı | Güvenli veri bağlama ve temiz DataFrame üretimi |
| **AI / NLP Mühendisi** | Text-to-SQL, Agentic Workflow (LangChain/CrewAI), zaman serisi tahmin modelleri | Soruyu anlayıp arka planda doğru tahmini yapan AI beyni |
| **Full-Stack Geliştirici** | Chat arayüzü, grafik entegrasyonları, kullanıcı yönetim paneli, AWS/Cloud mimarisi | Kullanıcının login olup ajanla konuşabildiği web uygulaması |

---

## Teknoloji Yığını

| Katman | Teknolojiler |
|--------|-------------|
| **Backend** | Python, FastAPI |
| **AI Orchestration** | LangChain, CrewAI |
| **ML / Tahminleme** | Prophet, ARIMA, LightGBM, scikit-learn |
| **Veri İşleme** | Pandas |
| **Veri Tabanları** | PostgreSQL, MySQL, MongoDB |
| **Cloud / Depolama** | AWS S3, Snowflake, AWS Secrets Manager |
| **Güvenlik** | Microsoft Presidio (PII maskeleme), KVKK/GDPR uyumu |
| **Frontend** | Chart.js / D3.js |
| **Test** | Birim ve entegrasyon testleri |

---

## Jira

Sprint planlaması ve görev takibi Jira üzerinden yürütülmektedir. Her sprinte ait pano görüntüleri ve görev dökümü aşağıdaki klasörde bulunmaktadır:

📁 [`Jira/`](./Jira)

| Sprint | Klasör | İçerik |
|--------|--------|--------|
| **Sprint I** | [`Jira/Sprint-I/`](./Jira/Sprint-I) | [Pano Görseli 1](./Jira/Sprint-I/Sprint-1-jira.png) · [Pano Görseli 2](./Jira/Sprint-I/Sprint-I-jira-2.png) · [Görev Listesi (xlsx)](./Jira/Sprint-I/jira-sprint1.xlsx) |
| **Sprint II** | [`Jira/Sprint-II/`](./Jira/Sprint-II) | *(Yakında eklenecek)* |
| **Sprint III** | [`Jira/Sprint-III/`](./Jira/Sprint-III) | *(Yakında eklenecek)* |

---

## Daily Scrum

Her sprint boyunca gerçekleştirilen stand-up toplantılarına (haftada 2-3 kez) ait ekran görüntüleri aşağıdaki klasörde bulunmaktadır:

📁 [`Daily Scrum/`](./Daily%20Scrum)

| Sprint | Klasör | Görseller |
|--------|--------|-----------|
| **Sprint I** | [`Daily Scrum/Sprint-I/`](./Daily%20Scrum/Sprint-I) | [1](./Daily%20Scrum/Sprint-I/1000022584.jpg) · [2](./Daily%20Scrum/Sprint-I/1000022585.jpg) · [3](./Daily%20Scrum/Sprint-I/1000022586.jpg) · [4](./Daily%20Scrum/Sprint-I/1000022587.jpg) · [5](./Daily%20Scrum/Sprint-I/20260705-16590.jpg) |
| **Sprint II** | [`Daily Scrum/Sprint-II/`](./Daily%20Scrum/Sprint-II) | *(Yakında eklenecek)* |
| **Sprint III** | [`Daily Scrum/Sprint-III/`](./Daily%20Scrum/Sprint-III) | *(Yakında eklenecek)* |

---

## Ürün Durumu ve Sprint Güncellemeleri

Ürünün güncel durumuna, her sprint'te gerçekleştirilen değişikliklere ait ekran görüntüleri ve belgelerine aşağıdaki klasörden ulaşabilirsiniz:

📁 [`Ürün_Durumu_Kontrol/`](./Ürün_Durumu_Kontrol)

| Sprint | Klasör | İçerik |
|--------|--------|--------|
| **Sprint I** | [`Ürün_Durumu_Kontrol/Sprint-I/`](./Ürün_Durumu_Kontrol/Sprint-I) | FastAPI kurulumu, LangChain entegrasyonu, MySQL/MongoDB/PostgreSQL konnektör testleri, AWS S3 testi, şema çıkarıcı, PII maskeleme, logger testleri, CI yerel kontrolleri ve config yönetimi/health check testlerine ait ekran görüntüleri |
| **Sprint II** | [`Ürün_Durumu_Kontrol/Sprint-II/`](./Ürün_Durumu_Kontrol/Sprint-II) | *(Yakında eklenecek)* |
| **Sprint III** | [`Ürün_Durumu_Kontrol/Sprint-III/`](./Ürün_Durumu_Kontrol/Sprint-III) | *(Yakında eklenecek)* |








