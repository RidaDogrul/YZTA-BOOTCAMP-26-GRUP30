# **REVIEW TOPLANTISI ÖZET**



**Temel Çıktılar**

Sprint 1 kapsamında temel altyapı bileşenleri (PostgreSQL, MongoDB, Amazon, FastAPI sunucusu) kuruldu ve temel bağlantılar sağlandı. 

Henüz kullanıcıya sunulabilir bir ürün çıktısı mevcut değil; demo ancak Sprint 3'te yapılabilecek. 

Sprint 2'de ajanların geliştirilmesi, Sprint 3'te ise görselleştirme ve son kullanıcı arayüzü hedefleniyor. 



**Alınan Kararlar**

Demo ertelendi: Çalışan ürün çıktısı olmadığı için Sprint 1 demosu yapılamadı; Sprint 3'e bırakıldı. 

Kod açıklama toplantısı: Her üye kendi yazdığı kodun çalışma mantığını kısaca ekibe anlatacak; bütünleşik yapıyı anlamak için mini bir toplantı düzenlenecek. 

Ürün videosu: Tamamlandığında hem resmi platforma hem YouTube'a yüklenecek. 

Tek kullanıcı senaryosu önceliği: Tüm modülleri aynı anda geliştirmek yerine tek bir çalışan kullanıcı senaryosu önce tamamlanacak. 



**Tamamlanan İşler**

**Elif**: PostgreSQL , Amazon S3, MongoDB bağlantıları kuruldu; şema çıktısı doğrulandı; Swagger dokümantasyonu güncellendi. 

**Rida:** FastAPI sunucusu çalışır hale getirildi; temel port/bağlantı yapısı oluşturuldu; sunucu bağlantı çıktısı gösterildi. 

**Nimet:** PII anonimleştirme modülü geliştirildi (e-posta, telefon, TC kimlik maskeleme); JSON formatlı loglama ve log çıktılarında hassas veri maskeleme eklendi; 7 test başarıyla geçti.

**Recep**: Konfigürasyon yönetimi (.env, örnek dosya) düzenlendi; CI/CD pipeline'a otomatik kontrol (Ruff, MyPy, Pytest) eklendi; Docker Compose'a FastAPI desteği entegre edildi; gereksiz import temizlendi. 

**Sevde**: Veri temizleme pipeline'ı geliştirildi (medyan/interpolasyon, aykırı değer tespiti); mini demo oluşturuldu. 



**Engeller / Riskler**

Türkçe isim maskeleme: Serbest metinde Türkçe özel isimler algılanamıyor; geçici çözüm olarak İngilizce döküman veya sabit isim listesi kullanılabilir.

Sevde – tamamlanmayan görev: İkinci görev sprint sonuna yetişemedi; Sprint 2'ye devredildi. 

Rida – silinen dosya: Depoda yanlışlıkla bir dosya silindi. 

Sprint 2 yoğunluğu: Ajan geliştirme aşaması olduğundan Sprint 2'nin zorlu geçmesi bekleniyor. 



**Onay Bekleyen Konular**

Türkçe isim algılama sorununun çözüm yöntemi (NLP iyileştirme mi, İngilizce veri mi?) kesinleştirilmedi. 

Kod açıklama toplantısının zamanlaması belirlenmedi. 



**Aksiyon Maddeleri**

**Tüm ekip**: Kendi yazdıkları kodun çalışma mantığını özetleyecek; mini toplantıda paylaşacak.

**Sevde**: Tamamlanmayan ikinci görevi Sprint 2'de bitirecek. 

**Nimet**: Türkçe isim maskeleme sorununu Sprint 2'de yeniden ele alacak; çözülemezse İngilizce veri alternatifi değerlendirilecek. 



