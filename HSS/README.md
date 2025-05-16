# Hava Savunma Sistemi (HSS)

Hava Savunma Sistemi (HSS), yüksek performanslı bir hedef tespit ve takip sistemidir. Bu sistem, kamera görüntüsü üzerinde nesne tespiti yaparak tehdit olabilecek hedefleri izler ve gerektiğinde önlem alır.

## Güncelleme
**YOLOv4-tiny modeli entegre edildi!** YOLOv4-tiny ile daha hızlı ve verimli nesne tespiti mümkündür (GTX 1080 Ti üzerinde 371 FPS, Jetson Nano üzerinde 39 FPS performans).

## Özellikler

- Gerçek zamanlı hedef tespiti ve takibi
- Farklı çalışma modları:
  - Manual Atış Modu
  - Otomatik Atış Modu
  - Angajman Modu
- Arduino ile motor kontrol sistemi
- Gelişmiş güvenlik protokolleri
- Modern kullanıcı arayüzü

### Arayüz Modernizasyonu

HSS kullanıcı arayüzü, aşağıdaki modern özelliklerle tamamen yenilenmiştir:

#### Modern Tasarım
- **Yuvarlatılmış Köşeler**: Tüm panel ve butonlarda canvas tabanlı yuvarlatılmış köşeler
- **Gölge ve Derinlik Efektleri**: 3D benzeri butonlar ve paneller
- **Gradyent Arka Plan**: Dikey ve kenarlarda vurgu renklerle gradyent arka plan
- **Modern Renk Paleti**: Koyu tema üzerinde dikkat çekici vurgu renkleri

#### Gelişmiş Kullanıcı Deneyimi
- **Etkileşimli Butonlar**: Tıklama, hover ve etkileşim animasyonları
- **LED Durum Göstergeleri**: Sistem durumunu gösteren renkli LED'ler
- **Segmentli Panel Düzeni**: Sol tarafta kontrol, sağ tarafta görüntü ve bilgi panelleri
- **Gelişmiş Bilgi Göstergeleri**: Hedef takip bilgileri, sistem durumu ve log kayıtları

#### Performans Optimizasyonları
- **Kamera Çözünürlüğü**: 480x360'dan 640x480'e yükseltildi
- **YOLO İşleme Optimizasyonu**: Seçilebilir performans modları
- **UI Güncellemesi**: Verimli ve akıcı arayüz güncellemesi

## Gereksinimler

### Donanım

- Raspberry Pi 5
- AI Kartı
- Arduino Mega
- 2 adet Step Motor
- Lazer modülü
- Soğutma fanları
- Sıcaklık sensörü
- Kamera modülü
- Acil durdurma butonu

### Yazılım

Python bağımlılıkları:
```
# Python sanal ortam oluşturma
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# veya
venv\Scripts\activate  # Windows

# Bağımlılıkları yükleme
pip install -r requirements.txt
```

Arduino kütüphaneleri:
- ArduinoJson
- Stepper
- OneWire
- DallasTemperature

## Kurulum

1. Projeyi indirin
```bash
git clone <repo-url>
cd HSS
```

2. Python bağımlılıklarını yükleyin
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# veya
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. YOLOv4-tiny modeli
```bash
# YOLOv4-tiny modeli otomatik olarak models/ dizininde bulunmaktadır
# Eğer dosyalar eksikse şu komutları çalıştırın:
mkdir -p models
wget https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/yolov4-tiny.weights -P models/
wget https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg -P models/
```

4. Arduino kodunu yükleyin
```bash
# Arduino IDE ile arduino/hss_arduino.ino dosyasını yükleyin
```

5. Arduino bağlantı portunu yapılandırın
```bash
# config.py dosyasındaki ARDUINO_PORT değişkenini güncelleyin
```

## Çalıştırma

```bash
source venv/bin/activate  # Linux/macOS
# veya
venv\Scripts\activate  # Windows
python main.py
```

Arayüzsüz (headless) mod:
```bash
python main.py --headless
```

## Sistem Mimarisi

```
+------------------------------------------+
|          HAVA SAVUNMA SİSTEMİ            |
+------------------------------------------+

[Raspberry Pi 5] <-----> [AI Kartı (YOLOv4-tiny)]
       ^
       |
       v
[Arduino Mega] <-----> [Step Motorlar (2x)]
       ^                     ^
       |                     |
       v                     v
   [Lazer]             [Soğutma Fanları]

                       [Kamera]
                          |
                          v
                    [Görüntü Verileri]
```

### YOLOv4-tiny Performans Değerleri

- **Doğruluk:** 40.2% mAP@0.5 (MS COCO veri seti)
- **Hız:** 
  - 371 FPS - GTX 1080 Ti GPU
  - 39 FPS - Jetson Nano
  - 290 FPS - Jetson AGX Xavier
  - 42 FPS - Intel Core i7 CPU

YOLOv4-tiny, ağ mimarisi küçültülerek ve hesaplama maliyeti optimize edilerek, kenar cihazlarda (edge devices) yüksek performans gösterecek şekilde tasarlanmıştır. Orijinal YOLOv4'e göre daha düşük doğruluk değerleri sunarken, çok daha yüksek FPS oranlarına ulaşabilmektedir.

## Mod Açıklamaları

### Mod 1: Otomatik Takip, Manuel Ateş
- Sistem tüm balonları (kırmızı/mavi) otomatik takip eder
- Kullanıcı "ATEŞ" butonu ile manuel olarak ateş eder

### Mod 2: Otomatik Takip, Otomatik Ateş
- Sistem sadece düşman (kırmızı) balonları tespit eder ve takip eder
- Hedef kilitlendiğinde otomatik olarak ateş eder
- Dost (mavi) hedeflere ateş edilmez

### Mod 3: Angajman Modu
- QR kod ile tahta (A veya B) belirlenir
- Şekil ve renk kombinasyonu ile hedef belirlenir
- Kullanıcı angajmanı onaylar
- Sistem belirtilen tahtaya yönlenir ve sadece belirlenen hedefe ateş eder

## Güvenlik Özellikleri

- Acil durdurma butonu ile tüm sistem durdurulabilir
- Sıcaklık sensörü ile aşırı ısınma durumunda fanlar otomatik devreye girer
- Kritik sıcaklık durumunda sistem kendini korumaya alır
- Lazer için güvenlik kilidi ve zaman aşımı mekanizması
- Kısıtlanmış hareket bölgeleri

## Yazarlar

- [Yazar Adı]

## Lisans

Bu proje [Lisans Adı] ile lisanslanmıştır. Detaylar için LICENSE dosyasına bakın. 