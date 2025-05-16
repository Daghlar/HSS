![Uploading image.png…]()
# HSS - Hava Savunma Sistemi

HSS (Hava Savunma Sistemi), balon gibi hava hedeflerini otomatik veya manuel olarak tespit eden ve takip eden bir savunma simülasyon sistemidir.

## Özellikler

- **Üç Çalışma Modu**: Manuel atış, otomatik atış ve angajman modları
- **Gerçek zamanlı hedef tespiti**: YOLOv4 tabanlı nesne tanıma
- **Renkli hedef sınıflandırması**: Kırmızı/mavi balon ayrımı
- **Servo motor kontrolü**: Pan-tilt mekanizması kontrolü
- **Arduino entegrasyonu**: Donanım kontrol sistemi
- **Modern kullanıcı arayüzü**: Tkinter tabanlı arayüz

## Kurulum

### Gereksinimler

- Python 3.7+
- OpenCV
- NumPy
- PIL (Pillow)
- Tkinter
- PySerial (Arduino iletişimi için)

### Bağımlılıkların Kurulumu

```bash
pip install -r requirements.txt
```

### YOLO Modelinin İndirilmesi

YOLOv4-tiny ağırlıklarını ve konfigürasyon dosyalarını aşağıdaki komutla indirebilirsiniz:

```bash
python scripts/download_yolo.py
```

## Kullanım

Programı başlatmak için:

```bash
python main.py
```

Arayüzsüz modda çalıştırmak için:

```bash
python main.py --headless
```

## Modlar

1. **Manuel Atış**: Kullanıcı tarafından kontrol edilen manuel atış modu
2. **Otomatik Atış**: Sistem tarafından otomatik hedef tespiti ve atış
3. **Angajman**: Hedefleri tespit, takip ve öncelik sırasına göre angajman

## Konfigürasyon

Sistem ayarlarını `config.py` dosyasından düzenleyebilirsiniz:

- Kamera çözünürlüğü
- YOLO tespit eşikleri
- Arduino bağlantı ayarları
- Performans parametreleri

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için `LICENSE` dosyasına bakınız. 
