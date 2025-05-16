# GitHub'a Proje Yükleme Talimatları

GitHub'a HSS projesini yüklemek için aşağıdaki adımları izleyin:

## 1. GitHub'da Yeni Repository Oluşturma

1. GitHub hesabınıza giriş yapın: https://github.com/login
2. Sağ üst köşedeki "+" simgesine tıklayın ve "New repository" seçeneğini seçin
3. Repository adı olarak "HSS" veya "Hava-Savunma-Sistemi" gibi anlamlı bir ad girin
4. İsteğe bağlı olarak bir açıklama ekleyin: "Hava Savunma Sistemi projesi"
5. Repository'nin "Public" (herkese açık) veya "Private" (özel) olacağını seçin
6. "Initialize this repository with a README" seçeneğini işaretlemeyin
7. "Create repository" butonuna tıklayın

## 2. Yerel Repoyu GitHub'a Bağlama

GitHub repository'nizi oluşturduktan sonra, aşağıdaki komutları terminal üzerinden çalıştırın:

```bash
# GitHub repo URL'nizi aşağıdaki komutta kullanın
git remote add origin https://github.com/KULLANICI_ADINIZ/REPO_ADINIZ.git

# Ana dalı GitHub'a gönderin
git push -u origin main
```

GitHub kullanıcı adınızı ve şifrenizi/kişisel erişim token'ınızı girmeniz istenecektir.

## 3. Değişiklikleri Push Etme

İlerleyen zamanlarda projede yaptığınız değişiklikleri GitHub'a yüklemek için:

```bash
# Değişiklikleri ekleyin
git add .

# Commit oluşturun
git commit -m "Değişiklik açıklaması"

# GitHub'a gönderin
git push
```

## 4. Repository Bağlantısı için Alternatif Yöntem (SSH)

Eğer SSH anahtarınız varsa ve GitHub'a eklediyseniz:

```bash
git remote add origin git@github.com:KULLANICI_ADINIZ/REPO_ADINIZ.git
git push -u origin main
```

## Proje Yapısı

GitHub'a yüklendikten sonra, projeniz aşağıdaki yapıda olacaktır:

```
HSS/
├── config.py               # Ana konfigürasyon dosyası
├── .gitignore              # Git tarafından yok sayılacak dosyalar
├── LICENSE                 # MIT lisans dosyası
├── README.md               # Proje dokümantasyonu
├── requirements.txt        # Python bağımlılıkları
├── HSS/                    # Ana proje dizini
│   ├── arduino/            # Arduino kontrol kodları
│   ├── control/            # Motor ve lazer kontrol modülleri
│   ├── gui/                # Kullanıcı arayüzü bileşenleri
│   ├── models/             # YOLO modelleri
│   ├── modes/              # Çalışma modları (manuel, otomatik, angajman)
│   ├── ui/                 # UI elemanları
│   ├── utils/              # Yardımcı fonksiyonlar
│   ├── vision/             # Görüntü işleme ve nesne tanıma
│   ├── config.py           # Detaylı konfigürasyon
│   ├── main.py             # Ana uygulama girişi
│   └── README.md           # İç dokümantasyon
└── logs/                   # Sistem log dosyaları (gitignore'da)
```

## Not

- GitHub'a ilk kez bağlanıyorsanız, kimlik doğrulama isteyecektir
- Ağustos 2021'den sonra GitHub şifre yerine kişisel erişim token'ı (Personal Access Token) kullanmanızı isteyebilir
- Kişisel erişim token'ı oluşturmak için: GitHub > Settings > Developer settings > Personal access tokens 