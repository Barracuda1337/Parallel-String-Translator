# Parallel String Translator 🌐

Bu proje, büyük metin dosyalarını paralel işleme kullanarak hızlı bir şekilde çeviren bir Python uygulamasıdır. Özellikle oyun lokalizasyonu gibi büyük çeviri projeleri için tasarlanmıştır.

## 🚀 Özellikler

- **Paralel İşleme**: Aynı anda 16 parçayı paralel olarak çevirir
- **Otomatik Kurtarma**: Elektrik kesintisi veya hata durumunda kaldığı yerden devam eder
- **İlerleme Takibi**: Her parça için detaylı ilerleme bilgisi
- **Güvenli Kayıt**: Her 10 satırda bir otomatik kayıt
- **Hata Toleransı**: Çeviri hatalarında 3 kez yeniden deneme
- **Bellek Optimizasyonu**: Büyük dosyaları parçalara bölerek işler

## 📋 Gereksinimler

```bash
Python 3.x
deep-translator
chardet
```

## 🛠️ Kurulum

1. Gereksinimleri yükleyin:
```bash
pip install deep-translator chardet
```

2. Projeyi klonlayın:
```bash
git clone https://github.com/Barracuda1337/Parallel-String-Translator.git
cd parallel-translator
```

## 💻 Kullanım

1. Çevrilecek dosyayı projenin ana dizinine kopyalayın
2. Dosya adını `index.py` içinde güncelleyin
3. Programı çalıştırın:
```bash
python py.py
```

### 📝 Dosya Formatı

Giriş dosyası aşağıdaki formatta olmalıdır:
```
KEY "çevrilecek metin"
ANOTHER_KEY "başka bir metin"
```

## ⚙️ Özelleştirme

`index.py` dosyasında aşağıdaki ayarları değiştirebilirsiniz:

- `max_processes`: Aynı anda işlenecek parça sayısı
- `lines_per_part`: Her parçadaki satır sayısı
- `source_lang`: Kaynak dil kodu
- `target_lang`: Hedef dil kodu

## 📊 Performans

- 14,000+ satırlık bir dosya için yaklaşık işlem süresi: 30-45 dakika
- Her parça ~146 satır içerir
- 16 paralel işlem ile optimum performans

## 🔄 İş Akışı

1. Dosya işlemci sayısına göre parçaya bölünür
2. Her parça ayrı bir işlemde çevrilir
3. İlerleme bilgisi JSON dosyalarında saklanır
4. Tamamlanan parçalar birleştirilir
5. Geçici dosyalar temizlenir (isteğe bağlı)

## 🛡️ Güvenlik Özellikleri

- UTF-8 ve UTF-16 kodlama desteği
- Otomatik dosya kodlaması tespiti
- Düzenli yedekleme ve ilerleme kaydı
- Hata durumunda orijinal metin koruma

## 🤝 Katkıda Bulunma

1. Bu depoyu fork edin
2. Yeni bir branch oluşturun (`git checkout -b feature/amazing`)
3. Değişikliklerinizi commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/amazing`)
5. Pull Request oluşturun

## 📝 Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## ✨ Teşekkürler

- Google Translate API
- Python Multiprocessing
- Deep Translator kütüphanesi

## 📞 İletişim

GitHub Issues üzerinden soru sorabilir ve önerilerde bulunabilirsiniz. 
