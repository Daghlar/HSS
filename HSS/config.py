"""
Hava Savunma Sistemi (HSS) için yapılandırma dosyası
"""

# Donanım bağlantıları
ARDUINO_PORT = "DUMMY"  # Arduino test modu - gerçek bağlantı için "/dev/ttyACM0" kullanın
ARDUINO_BAUDRATE = 115200       # Seri iletişim hızı

# Kamera ve görüntü ayarları
CAMERA_ID = -1                  # Test modu için -1, gerçek kamera için 0 veya başka ID
CAMERA_WIDTH = 480              # Kamera genişliği (düşük çözünürlük - performans için)
CAMERA_HEIGHT = 360             # Kamera yüksekliği (düşük çözünürlük - performans için)
CAMERA_FPS = 30                 # Kamera FPS

# YOLO yapılandırması
YOLO_CONFIG_PATH = "models/yolov4-tiny.cfg"
YOLO_WEIGHTS_PATH = "models/yolov4-tiny.weights"
YOLO_CONFIDENCE_THRESHOLD = 0.5  # Tespit güven eşiği (düşürüldü - daha hızlı tespit için)
YOLO_NMS_THRESHOLD = 0.5         # NMS eşiği (yükseltildi - daha hızlı birleştirme için)
YOLO_INPUT_SIZE = 256            # YOLO giriş boyutu (küçültüldü - daha hızlı tespit için)
YOLO_PROCESS_EVERY_N_FRAME = 5   # Her N karede bir YOLO işlemi yap (arttırıldı - daha iyi performans için)
YOLO_DETECTION_CLASSES = ["balloon", "red_balloon", "blue_balloon"]  # Öncelikli tespit sınıfları

# Motor parametreleri
MOTOR_HORIZONTAL_RANGE = 270    # Yatay hareket aralığı (derece)
MOTOR_VERTICAL_RANGE = 60       # Dikey hareket aralığı (derece)
MOTOR_SPEED = 50                # Motor hızı
MOTOR_ACCELERATION = 25         # Motor ivmesi

# Lazer parametreleri
LASER_TIMEOUT = 2.0             # Lazer aktif kalma süresi (saniye)

# Sistem güvenlik parametreleri
MAX_TEMPERATURE = 75.0          # Maksimum sıcaklık (Celcius)
EMERGENCY_STOP_PIN = 17         # Acil durdurma butonu pini
SAFETY_TIMEOUT = 300            # Güvenlik zaman aşımı (saniye)

# Mod parametreleri
MODE_TIMEOUT = 300              # Her mod için zaman sınırı (saniye)

# Angajman parametreleri
BOARD_A_POSITION = -45          # A tahtasının açı pozisyonu (saat 10 yönü)
BOARD_B_POSITION = 45           # B tahtasının açı pozisyonu (saat 2 yönü)

# Yasak bölgeler (açı aralıkları)
RESTRICTED_ZONES = [
    {"horizontal": (-180, -90), "vertical": (0, 60)},
    {"horizontal": (90, 180), "vertical": (0, 60)}
]

# Hedef renkleri
TARGET_COLORS = {
    "RED": ((0, 100, 100), (10, 255, 255)),     # Düşman (HSV alt ve üst değerleri)
    "BLUE": ((100, 100, 100), (130, 255, 255))  # Dost (HSV alt ve üst değerleri)
}

# Geometrik şekiller
TARGET_SHAPES = ["CIRCLE", "SQUARE", "TRIANGLE"]

# JSON mesaj formatları
JSON_MESSAGE_TEMPLATES = {
    "motor_command": {
        "type": "motor",
        "horizontal": 0,  # Derece
        "vertical": 0,    # Derece
        "speed": 50       # 0-100 arası
    },
    "laser_command": {
        "type": "laser",
        "state": False,   # True/False
        "duration": 0     # Saniye
    },
    "status_request": {
        "type": "status"
    },
    "fan_command": {
        "type": "fan",
        "state": False    # True/False
    }
}

# Performans optimizasyonu
ENABLE_GPU_ACCELERATION = True   # GPU hızlandırma kullan
LOW_PERFORMANCE_MODE = False     # Düşük performans modunu devre dışı bırak
UI_UPDATE_RATE = 200             # UI güncelleme hızı (ms) (arttırıldı - daha az yüklenme için)
MAX_LOG_LINES = 15               # Maksimum log satırı (azaltıldı - daha az bellek kullanımı)
LOG_TO_CONSOLE = False           # Konsola log yazma (performans için kapatıldı)
DISABLE_UI_ANIMATIONS = True     # UI animasyonları devre dışı (performans için)
SKIP_YOLO_DETECTION = 2          # YOLO tespitini n kare atla (arttırıldı - performans için)
SKIP_UI_UPDATES = 1              # Her n karede bir UI güncelle (performans için)
USE_DIRECT_RENDERING = True      # Doğrudan render kullan (performans için)

# Test ve Mock modlar
TEST_MODE = True          # Test modunu aktifleştir
MOCK_ARDUINO = True       # Arduino bağlantısını mockla
MOCK_CAMERA = True        # Kamera bağlantısını mockla
MOCK_DETECTOR = True      # YOLO Dedektörünü mockla 