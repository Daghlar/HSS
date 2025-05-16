"""
Hava Savunma Sistemi (HSS) ana program dosyası.
Tüm sistem bileşenlerini başlatır ve ana döngüyü yönetir.
"""

import os
import sys
import time
import signal
import logging
import argparse
import cv2
import numpy as np

# Modülleri içe aktar
from config import *

# Test modu için mock sınıflar
class MockArduinoComm:
    def __init__(self, port, baudrate):
        self.port = port
        self.baudrate = baudrate
        self.logger = logging.getLogger('MockArduino')
        self.logger.info("Mock Arduino oluşturuldu")
        
    def initialize(self):
        self.logger.info("Mock Arduino başlatıldı")
        return True
        
    def is_connected(self):
        return True
        
    def get_servo_position(self, servo_id):
        if servo_id == 1:
            return 90  # X ekseni
        else:
            return 45  # Y ekseni
            
    def emergency_stop(self):
        self.logger.warning("ACİL DURDURMA çağrıldı")
        
    def close(self):
        self.logger.info("Mock Arduino kapatıldı")

class MockCamera:
    def __init__(self, camera_id, width, height, fps):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self.logger = logging.getLogger('MockCamera')
        
        # Demo için siyah ekran oluştur
        self.dummy_frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.putText(self.dummy_frame, "HSS - Demo Kamera Görüntüsü", (50, height//2),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        
    def initialize(self):
        self.logger.info("Mock kamera başlatıldı")
        return True
        
    def get_frame(self):
        # Basit hareket eden noktalar çiz (demo amaçlı)
        frame = self.dummy_frame.copy()
        t = time.time()
        
        # Hareket eden nokta
        x = int(self.width/2 + np.sin(t) * self.width/4)
        y = int(self.height/2 + np.cos(t) * self.height/4)
        cv2.circle(frame, (x, y), 15, (0, 0, 255), -1)
        
        return True, frame
        
    def is_working(self):
        return True
        
    def release(self):
        self.logger.info("Mock kamera kapatıldı")

class MockYoloDetector:
    def __init__(self, config_path, weights_path, conf_threshold, nms_threshold):
        self.config_path = config_path
        self.weights_path = weights_path
        self.confidence_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.logger = logging.getLogger('MockYOLO')
        
    def initialize(self):
        self.logger.info("Mock YOLO başlatıldı")
        return True
        
    def detect(self, frame):
        # Demo amaçlı rastgele dedektör sonuçları
        height, width = frame.shape[:2]
        
        # %30 olasılıkla tespit yap
        if np.random.random() < 0.3:
            # Ekranın ortasında rastgele boyutta bir nesne
            x = np.random.randint(width//4, width*3//4)
            y = np.random.randint(height//4, height*3//4)
            w = np.random.randint(50, 150)
            h = np.random.randint(50, 150)
            
            detection = {
                "box": [x, y, w, h],
                "confidence": np.random.random() * 0.5 + 0.5,  # 0.5-1.0 arası
                "class": "balon" if np.random.random() < 0.7 else "insan",
                "color": "kirmizi" if np.random.random() < 0.5 else "mavi"
            }
            return [detection]
        else:
            return []
            
    def classify_balloons(self, frame, detections):
        # Her balona bir renk ata
        for detection in detections:
            if detection.get("class") == "balon" and not "color" in detection:
                detection["color"] = "kirmizi" if np.random.random() < 0.5 else "mavi"
        return detections

class MockQRDetector:
    def __init__(self):
        self.logger = logging.getLogger('MockQR')
        
    def detect(self, frame):
        # Nadiren QR kod tespit et
        if np.random.random() < 0.05:
            return [{"data": "A" if np.random.random() < 0.5 else "B"}]
        return []

class MockSafetyMonitor:
    def __init__(self, arduino):
        self.arduino = arduino
        self.logger = logging.getLogger('MockSafety')
        self.motor_controller = self  # Kendisini motor kontrolcü olarak kullan
        self.laser_controller = self  # Kendisini lazer kontrolcü olarak da kullan
        
    def start_monitoring(self):
        self.logger.info("Mock güvenlik izleme başlatıldı")
        
    def is_system_safe(self):
        return True
        
    def shutdown(self):
        self.logger.info("Mock güvenlik izleme kapatıldı")
        
    def calibrate(self):
        self.logger.info("Mock motor kalibrasyonu yapıldı")
        return True
        
    def advanced_calibration(self):
        self.logger.info("Mock gelişmiş kalibrasyon yapıldı")
        return True

# Gerçek modüleri içe aktar - Mock modundayken içe aktar (eğer bulunamazsa hata vermesin diye)
try:
    from utils.safety import SafetyMonitor
    from vision.camera import Camera
    from vision.yolo_detector import YoloDetector
    from vision.qr_detector import QRDetector
    from control.arduino_comm import ArduinoComm
    from modes.mode1_manual_fire import Mode1
    from modes.mode2_auto_fire import Mode2
    from modes.mode3_engagement import Mode3
except ImportError:
    # Test modunda bu modüller yoksa dummy modüller oluştur
    class Mode1:
        def __init__(self, camera, detector, arduino, safety):
            self.camera = camera
            self.detector = detector
            self.arduino = arduino
            self.safety = safety
            
        def run(self, user_input):
            pass
            
    class Mode2(Mode1):
        pass
        
    class Mode3(Mode1):
        pass

# Kullanıcı arayüzü ve görselleştirme
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

# Canvas için yuvarlatılmış dikdörtgen desteği ekle
def _create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
    """
    Yuvarlatılmış kenarları olan bir dikdörtgen çizer.
    
    Args:
        x1, y1: Sol üst köşe koordinatları
        x2, y2: Sağ alt köşe koordinatları
        radius: Köşe yarıçapı
        **kwargs: Diğer Canvas parametreleri
    
    Returns:
        int: Çizilen dikdörtgenin ID'si
    """
    points = [
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1
    ]
    
    # Köşelere eğri eklemek için özelleştirilmiş
    return self.create_polygon(points, **kwargs, smooth=True)

# Metodu Canvas'a ekle
tk.Canvas.create_rounded_rectangle = _create_rounded_rectangle

class HSSSystem:
    """
    Hava Savunma Sistemi (HSS) ana sınıf.
    """
    
    def __init__(self):
        """
        HSS sistemini başlatır.
        """
        # Loglama ayarları
        self._setup_logging()
        
        self.logger = logging.getLogger("HSSSystem")
        self.logger.info("Hava Savunma Sistemi başlatılıyor...")
        
        # Ana bileşenleri başlat
        self._initialize_components()
        
        # Modları başlat
        self._initialize_modes()
        
        # Ana döngü durumu
        self.running = False
        self.current_mode = 1  # Başlangıç modu
        
        # Acil durdurma sinyalini yakala
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Kullanıcı arayüzü
        self.ui_root = None
        self.ui_frame = None
        self.mode_var = None
        self.fire_button = None
        self.status_label = None
        self.camera_label = None
        
        # Durum göstergeleri için sözlükler
        self.status_indicators = {}
        self.status_leds = {}
        
        self.user_input = {
            "fire": False,
            "confirm_engagement": False,
            "cancel_engagement": False,
            "selected_target": None
        }
        
        self.logger.info("Hava Savunma Sistemi başlatıldı")
    
    def _setup_logging(self):
        """
        Loglama ayarlarını yapılandırır.
        """
        # Log dizinini oluştur
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Log formatını ayarla
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Handlers listesini oluştur
        handlers = [logging.FileHandler(os.path.join(log_dir, "hss.log"))]
        
        # Konsola log yazma ayarını kontrol et
        from config import LOG_TO_CONSOLE
        if not hasattr(sys.modules['config'], 'LOG_TO_CONSOLE') or LOG_TO_CONSOLE:
            handlers.append(logging.StreamHandler())
        
        # Loglama seviyesini ayarla (performans için WARNING kullan)
        log_level = logging.WARNING if hasattr(sys.modules['config'], 'LOW_PERFORMANCE_MODE') and LOW_PERFORMANCE_MODE else logging.INFO
        
        logging.basicConfig(
            level=log_level,
            format=log_format,
            handlers=handlers
        )
    
    def _initialize_components(self):
        """
        Ana sistem bileşenlerini başlatır.
        """
        try:
            # Arduino iletişimini başlat
            self.arduino = MockArduinoComm(ARDUINO_PORT, ARDUINO_BAUDRATE)
            if not self.arduino.initialize():
                self.logger.error("Arduino bağlantısı kurulamadı")
                sys.exit(1)
            
            # Güvenlik izleyiciyi başlat
            self.safety = MockSafetyMonitor(self.arduino)
            
            # Kamerayı başlat
            self.camera = MockCamera(
                CAMERA_ID,
                CAMERA_WIDTH,
                CAMERA_HEIGHT,
                CAMERA_FPS
            )
            if not self.camera.initialize():
                self.logger.error("Kamera başlatılamadı")
                sys.exit(1)
            
            # YOLO detektörünü başlat
            self.detector = MockYoloDetector(
                YOLO_CONFIG_PATH,
                YOLO_WEIGHTS_PATH,
                YOLO_CONFIDENCE_THRESHOLD,
                YOLO_NMS_THRESHOLD
            )
            if not self.detector.initialize():
                self.logger.error("YOLO dedektörü başlatılamadı")
                sys.exit(1)
            
            self.logger.info("YOLOv4-tiny dedektörü başarıyla başlatıldı")
            
            # QR kod dedektörünü başlat
            self.qr_detector = MockQRDetector()
            
            self.logger.info("Sistem bileşenleri başarıyla başlatıldı")
            
        except Exception as e:
            self.logger.error(f"Bileşenler başlatılırken hata: {str(e)}")
            sys.exit(1)
    
    def _initialize_modes(self):
        """
        Sistem modlarını başlatır.
        """
        # Modları oluştur
        self.mode1 = Mode1(self.camera, self.detector, self.arduino, self.safety)
        self.mode2 = Mode2(self.camera, self.detector, self.arduino, self.safety)
        self.mode3 = Mode3(self.camera, self.detector, self.arduino, self.safety)
        
        self.logger.info("Sistem modları başlatıldı")
    
    def _signal_handler(self, sig, frame):
        """
        Sinyal yakalayıcı (Ctrl+C vb.).
        """
        self.logger.info("Kapatma sinyali alındı, sistem kapatılıyor...")
        self.stop()
        sys.exit(0)
    
    def _create_ui(self):
        """
        Kullanıcı arayüzünü oluşturur.
        """
        self.ui_root = tk.Tk()
        self.ui_root.title("HSS - HAVA SAVUNMA SİSTEMİ KONTROL MERKEZİ")
        self.ui_root.geometry("1280x800")
        
        # Modern koyu arka plan
        self.ui_root.configure(bg="#111827")  # Koyu endüstriyel tema
        
        # Gradyent arka plan oluşturmak için canvas ekle
        self.bg_canvas = tk.Canvas(self.ui_root, highlightthickness=0)
        self.bg_canvas.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Gradyent çizim fonksiyonu
        def draw_gradient():
            width = self.ui_root.winfo_width()
            height = self.ui_root.winfo_height()
            
            if width <= 1 or height <= 1:
                # Boyutlar henüz hazır değil, tekrar dene
                self.ui_root.after(100, draw_gradient)
                return
                
            # Gradyent için renkler
            top_color = "#0F1729"     # Koyu lacivert (üst)
            mid_color = "#111827"     # Standart arka plan (orta)
            bottom_color = "#0D1424"  # Daha koyu (alt)
            
            # Vurgu rengi için küçük bir yan gradyent
            accent_color = "#3B82F6"  # Mavi
            accent_dark = "#1E40AF"   # Koyu mavi
            
            # En üstte koyu gradyent bölge
            self.bg_canvas.delete("gradient")
            
            # Dikey gradyent (üst->orta->alt)
            for i in range(height):
                # İlk %40 üst->orta
                if i < height * 0.4:
                    ratio = i / (height * 0.4)
                    r = int(int(top_color[1:3], 16) * (1-ratio) + int(mid_color[1:3], 16) * ratio)
                    g = int(int(top_color[3:5], 16) * (1-ratio) + int(mid_color[3:5], 16) * ratio)
                    b = int(int(top_color[5:7], 16) * (1-ratio) + int(mid_color[5:7], 16) * ratio)
                # Son %60 orta->alt
                else:
                    ratio = (i - height * 0.4) / (height * 0.6)
                    r = int(int(mid_color[1:3], 16) * (1-ratio) + int(bottom_color[1:3], 16) * ratio)
                    g = int(int(mid_color[3:5], 16) * (1-ratio) + int(bottom_color[3:5], 16) * ratio)
                    b = int(int(mid_color[5:7], 16) * (1-ratio) + int(bottom_color[5:7], 16) * ratio)
                
                color = f"#{r:02x}{g:02x}{b:02x}"
                self.bg_canvas.create_line(0, i, width, i, fill=color, tags="gradient")
            
            # Kenarlarda vurgu rengi gradyenti (sol ve sağ)
            for i in range(width // 10):  # Ekranın %10'u kadar
                # Sol kenar
                ratio = i / (width // 10)
                rev_ratio = 1 - ratio
                r = int(int(accent_color[1:3], 16) * rev_ratio * 0.2 + int(mid_color[1:3], 16) * (1 - rev_ratio * 0.2))
                g = int(int(accent_color[3:5], 16) * rev_ratio * 0.2 + int(mid_color[3:5], 16) * (1 - rev_ratio * 0.2))
                b = int(int(accent_color[5:7], 16) * rev_ratio * 0.2 + int(mid_color[5:7], 16) * (1 - rev_ratio * 0.2))
                left_color = f"#{r:02x}{g:02x}{b:02x}"
                
                # Sağ kenar
                right_x = width - i
                r = int(int(accent_dark[1:3], 16) * rev_ratio * 0.15 + int(mid_color[1:3], 16) * (1 - rev_ratio * 0.15))
                g = int(int(accent_dark[3:5], 16) * rev_ratio * 0.15 + int(mid_color[3:5], 16) * (1 - rev_ratio * 0.15))
                b = int(int(accent_dark[5:7], 16) * rev_ratio * 0.15 + int(mid_color[5:7], 16) * (1 - rev_ratio * 0.15))
                right_color = f"#{r:02x}{g:02x}{b:02x}"
                
                self.bg_canvas.create_line(i, 0, i, height, fill=left_color, tags="gradient")
                self.bg_canvas.create_line(right_x, 0, right_x, height, fill=right_color, tags="gradient")
                
        # Pencere boyutu değiştiğinde gradyenti yeniden çiz
        def resize_bg(event):
            self.ui_root.after(100, draw_gradient)
            
        self.ui_root.bind("<Configure>", resize_bg)
        
        # İlk gradyenti çiz
        self.ui_root.after(100, draw_gradient)
        
        # Yeni değişkenleri başlat
        self.status_indicators = {}
        self.status_leds = {}
        
        # UI güncellemesi hızı (config'den al)
        from config import UI_UPDATE_RATE
        self.ui_update_rate = UI_UPDATE_RATE if 'UI_UPDATE_RATE' in globals() else 30  # msec
        
        # Kare sayacı ve YOLO işlem kontrolü
        self.frame_count = 0
        self.process_yolo = True
        self.yolo_process_frame_count = 0
        
        # UI çizim optimizasyonu
        cv2.setUseOptimized(True)
        
        # Çoklu işlem için flag
        self.is_processing = False
        
        # İkon ayarla
        try:
            if os.path.exists("HSS/assets/icon.ico"):
                self.ui_root.iconbitmap("HSS/assets/icon.ico")
        except Exception:
            pass
        
        # Ana çerçeve
        main_frame = ttk.Frame(self.ui_root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Stil oluştur - modern tasarım
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Ana renk paleti - modern koyu tema
        bg_color = "#111827"          # Koyu arka plan (slate-900)
        panel_bg = "#1E293B"          # Panel arka planı (slate-800)
        indicator_bg = "#0F172A"      # Gösterge arka planı (slate-900 darker)
        accent_color = "#3B82F6"      # Mavi vurgu (blue-500)
        accent_dark = "#2563EB"       # Koyu mavi (blue-600)
        highlight_color = "#F43F5E"   # Kırmızı vurgu (rose-500)
        text_color = "#F1F5F9"        # Açık metin (slate-100)
        secondary_text = "#94A3B8"    # İkincil metin (slate-400)
        success_color = "#10B981"     # Yeşil (emerald-500)
        warning_color = "#F59E0B"     # Sarı (amber-500)
        danger_color = "#EF4444"      # Kırmızı (red-500)
        info_color = "#3B82F6"        # Mavi (blue-500)
        
        # Özel canvas renkleri
        self.ui_colors = {
            'bg': bg_color,
            'panel': panel_bg,
            'indicator': indicator_bg,
            'accent': accent_color,
            'accent_dark': accent_dark,
            'highlight': highlight_color,
            'text': text_color,
            'secondary_text': secondary_text,
            'success': success_color,
            'warning': warning_color,
            'danger': danger_color,
            'info': info_color
        }
        
        # Stil ayarları
        self.style.configure('TFrame', background=bg_color)
        self.style.configure('TLabel', background=bg_color, foreground=text_color, font=('Roboto', 10))
        self.style.configure('Panel.TFrame', background=panel_bg)
        self.style.configure('Panel.TLabel', background=panel_bg, foreground=text_color)
        self.style.configure('Indicator.TFrame', background=indicator_bg)
        self.style.configure('Indicator.TLabel', background=indicator_bg, foreground=text_color)
        self.style.configure('Value.TLabel', background=indicator_bg, foreground="#FFFFFF", 
                           font=('Roboto Mono', 11, 'bold'))
        
        # LED gösterge stilleri
        self.style.configure('LED.TFrame', background=panel_bg)
        self.style.configure('LED.Normal.TFrame', background=info_color)
        self.style.configure('LED.Warning.TFrame', background=warning_color)
        self.style.configure('LED.Error.TFrame', background=danger_color)
        self.style.configure('LED.Success.TFrame', background=success_color)
        
        # Buton stilleri - artık canvas kullanacağız, bu stiller sadece destek amaçlı
        self.style.configure('TButton', background=accent_color, foreground=text_color, 
                           padding=8, font=('Roboto', 10, 'bold'))
        self.style.configure('Accent.TButton', background=highlight_color)
        self.style.configure('Success.TButton', background=success_color)
        self.style.configure('Warning.TButton', background=warning_color, foreground="#000000")
        self.style.configure('Danger.TButton', background=danger_color)
        
        # Mod göstergeleri için özel stiller
        self.style.configure('Mode.TFrame', background=panel_bg)
        self.style.configure('ModeActive.TLabel', background=highlight_color, foreground=text_color, 
                          font=('Roboto', 11, 'bold'), padding=10)
        self.style.configure('ModeInactive.TLabel', background=panel_bg, foreground=text_color, 
                           font=('Roboto', 11), padding=10)
        self.style.configure('ModeHover.TLabel', background=panel_bg, foreground="#E0E0E0", 
                           font=('Roboto', 11, 'bold'), padding=10)
        
        # Başlık ve gösterge stilleri
        self.style.configure('Header.TLabel', font=('Roboto', 16, 'bold'), foreground=highlight_color)
        self.style.configure('Subheader.TLabel', font=('Roboto', 12, 'bold'), foreground=text_color)
        self.style.configure('Status.TLabel', font=('Roboto', 11, 'bold'), background=indicator_bg, foreground=text_color)
        self.style.configure('Critical.TLabel', foreground=danger_color)
        self.style.configure('Warning.TLabel', foreground=warning_color)
        self.style.configure('Success.TLabel', foreground=success_color)
        self.style.configure('Info.TLabel', foreground=info_color)
        
        # LabelFrame stilleri
        self.style.configure('TLabelframe', background=panel_bg)
        self.style.configure('TLabelframe.Label', background=bg_color, foreground=highlight_color, 
                           font=('Roboto', 12, 'bold'))
        
        # Ana pencerenin iki kısma bölünmesi: sol panel ve sağ içerik
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)
        
        # Sol taraf - Kontrol Paneli (3 bölüm)
        left_frame = ttk.Frame(paned_window, width=350, style='TFrame')
        paned_window.add(left_frame, weight=1)
        
        # Sağ taraf - Görüntü ve durum
        right_frame = ttk.Frame(paned_window, style='TFrame')
        paned_window.add(right_frame, weight=4)
        
        # Sol panel bölümleri için ana çerçeve
        left_section_frame = ttk.Frame(left_frame, style='TFrame')
        left_section_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)
        
        # Sol panel üst bölüm - Sistem modları
        self._create_rounded_frame(left_section_frame, "SİSTEM MODU", self._create_mode_section, 
                                    pady=(0, 10), padx=5)
        
        # Sol panel orta bölüm - Kontrol Komutları
        self._create_rounded_frame(left_section_frame, "KONTROL KOMUTLARI", self._create_controls_section, 
                                    pady=10, padx=5)
        
        # Sol panel alt bölüm - Sistem Durumu ve Uyarılar
        self._create_rounded_frame(left_section_frame, "SİSTEM DURUMU", self._create_status_section, 
                                    pady=(10, 0), padx=5, expand=True)
        
        # Sağ Panel - Kamera ve Görüntü İşleme - modern tasarım
        self._create_camera_panel(right_frame)
        
        # Hedef takip bilgisi
        self._create_target_panel(right_frame)
        
        # Alt bilgi paneli - tespit bilgileri
        self._create_info_panel(right_frame)
        
        # Log alanı - sağ alt köşede
        self._create_log_panel(right_frame)
        
        # Özel log işleyici
        self.log_handler = LogHandler(self)
        logging.getLogger().addHandler(self.log_handler)
        
        # Mod değişikliği dinleyicisi - sadece değer değişimini izle
        self.mode_var.trace_add("write", self._mode_changed)
        
        # UI güncellemesi ve sistem döngüsü
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.fps = 0
        
        # CPU Kullanımını takip et
        self.ui_root.after(1000, self._update_cpu_usage)
        
        # Arayüz tespiti
        self.is_ui_focused = True
        self.ui_root.bind("<FocusIn>", lambda e: self._ui_focus_changed(True))
        self.ui_root.bind("<FocusOut>", lambda e: self._ui_focus_changed(False))
        
        # İlk UI güncellemesini başlat
        self.ui_root.after(100, self._update_ui)
        self.ui_root.after(10, self.run_system_loop)
        
        # Butonların durumunu güncelle
        self._update_buttons()
    
    def _create_rounded_frame(self, parent, title, content_func, **kwargs):
        """
        Yuvarlatılmış köşeli çerçeve oluşturur.
        
        Args:
            parent: Üst widget
            title: Çerçeve başlığı
            content_func: İçerik oluşturan fonksiyon
            **kwargs: Pack parametreleri
        
        Returns:
            tuple: (çerçeve, içerik çerçevesi)
        """
        # Çerçeve arka planı
        frame = ttk.Frame(parent, style='TFrame')
        frame.pack(fill=tk.BOTH, **kwargs)
        
        # Başlık etiket 
        header_label = ttk.Label(frame, text=title, style='TLabelframe.Label')
        header_label.pack(anchor=tk.NW, padx=15, pady=(0, 5))
        
        # İçerik çerçevesi
        content_canvas = tk.Canvas(frame, bg=self.ui_colors['panel'], highlightthickness=0)
        content_canvas.pack(fill=tk.BOTH, expand=kwargs.get('expand', False), padx=5, pady=5)
        
        # Yuvarlatılmış dikdörtgen çiz
        radius = 15
        width = content_canvas.winfo_reqwidth()
        height = content_canvas.winfo_reqheight()
        
        def draw_rounded_rectangle(event):
            width = event.width
            height = event.height
            content_canvas.delete("rounded_rect")
            content_canvas.create_rounded_rectangle(
                0, 0, width, height, radius=radius, 
                fill=self.ui_colors['panel'], outline="", tags="rounded_rect"
            )
            content_canvas.tag_lower("rounded_rect")
        
        content_canvas.bind("<Configure>", draw_rounded_rectangle)
        
        # İçerik çerçevesi 
        content_frame = ttk.Frame(content_canvas, style='Panel.TFrame')
        content_canvas.create_window(5, 5, anchor=tk.NW, window=content_frame, 
                                   tags="content", width=width-10, height=height-10)
        
        def update_window_size(event):
            width = event.width
            height = event.height
            content_canvas.itemconfig("content", width=width-10, height=height-10)
        
        content_canvas.bind("<Configure>", lambda e: (draw_rounded_rectangle(e), update_window_size(e)))
        
        # İçerik fonksiyonunu çağır
        content_func(content_frame)
        
        return frame, content_frame
    
    def _create_mode_section(self, parent):
        """
        Mod seçim bölümünü oluşturur.
        
        Args:
            parent: Üst widget
        """
        # Toggle butonları için bir çerçeve
        toggle_frame = ttk.Frame(parent, style='Panel.TFrame')
        toggle_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # Mod değişkeni
        self.mode_var = tk.IntVar(value=self.current_mode)
        
        # Toggle buton işlevselliği için
        self.mode_labels = []
        
        # Mod butonlarını oluştur
        modes = [
            {"num": 1, "text": "MANUEL ATIŞ", "color": self.ui_colors['danger']},
            {"num": 2, "text": "OTOMATİK ATIŞ", "color": self.ui_colors['info']},
            {"num": 3, "text": "ANGAJMAN", "color": self.ui_colors['warning']}
        ]
        
        for mode in modes:
            self._create_mode_button(toggle_frame, mode["num"], mode["text"], mode["color"])
        
        # Performans ayarı
        perf_frame = ttk.Frame(toggle_frame, style='Panel.TFrame')
        perf_frame.pack(fill=tk.X, pady=(15, 5), padx=5)
        ttk.Label(perf_frame, text="PERFORMANS MODU:", 
                style='Subheader.TLabel').pack(side=tk.LEFT, padx=5)
        
        # Performans açılır menüsü
        self.performance_var = tk.StringVar(value="Dengeli")
        performance_options = ["Yüksek Hız", "Dengeli", "Yüksek Kalite"]
        
        # Özel stilli OptionMenu
        opt_menu_style = {'highlightthickness': 0, 'bg': self.ui_colors['indicator'], 
                        'fg': self.ui_colors['text'], 'activebackground': self.ui_colors['accent'],
                        'activeforeground': self.ui_colors['text'], 'relief': 'flat'}
        
        opt_menu = tk.OptionMenu(perf_frame, self.performance_var, 
                               "Dengeli", *performance_options, 
                               command=self._performance_mode_changed)
        opt_menu.config(**opt_menu_style)
        opt_menu.pack(side=tk.RIGHT, padx=5)
    
    def _create_mode_button(self, parent, mode_num, text, color):
        """
        Mod butonu oluşturur (yuvarlatılmış).
        
        Args:
            parent: Üst widget
            mode_num: Mod numarası
            text: Buton metni
            color: Buton rengi
        """
        frame = ttk.Frame(parent, style='Panel.TFrame')
        frame.pack(fill=tk.X, pady=3)
        
        canvas_height = 40
        canvas = tk.Canvas(frame, bg=self.ui_colors['panel'], height=canvas_height, 
                         highlightthickness=0)
        canvas.pack(fill=tk.X, expand=True)
        
        # Buton arka planı
        is_active = self.current_mode == mode_num
        button_color = color if is_active else self.ui_colors['panel']
        text_color = self.ui_colors['text']
        
        def draw_button(color):
            canvas.delete("button")
            width = canvas.winfo_width()
            # Yuvarlatılmış buton çiz
            canvas.create_rounded_rectangle(0, 0, width, canvas_height, radius=10, 
                                         fill=color, outline="", tags="button")
            # Metin ekle
            canvas.create_text(width/2, canvas_height/2, text=text, 
                            font=('Roboto', 11, 'bold'), fill=text_color, tags="button")
        
        def update_button(event):
            width = event.width
            canvas.delete("button")
            canvas.create_rounded_rectangle(0, 0, width, canvas_height, radius=10, 
                                         fill=button_color, outline="", tags="button")
            canvas.create_text(width/2, canvas_height/2, text=text, 
                            font=('Roboto', 11, 'bold'), fill=text_color, tags="button")
        
        canvas.bind("<Configure>", update_button)
        
        # Tıklama olayı
        def on_click(event):
            self._toggle_mode(mode_num)
        
        # Hover olayları
        def on_enter(event):
            if self.current_mode != mode_num:
                hover_color = self._adjust_color(button_color, 1.2)
                draw_button(hover_color)
        
        def on_leave(event):
            if self.current_mode != mode_num:
                draw_button(button_color)
        
        canvas.bind("<Button-1>", on_click)
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        
        # Mod değişimi için referans
        self.mode_labels.append({"canvas": canvas, "mode": mode_num, "color": color})
    
    def _create_controls_section(self, parent):
        """
        Kontrol butonları bölümünü oluşturur.
        
        Args:
            parent: Üst widget
        """
        controls_frame = ttk.Frame(parent, style='Panel.TFrame')
        controls_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)
        
        # Üst sıra butonları
        top_buttons_frame = ttk.Frame(controls_frame, style='Panel.TFrame')
        top_buttons_frame.pack(fill=tk.X, pady=5)
        
        # Ateş butonu (Mod 1'de aktif)
        self.fire_button = self._create_rounded_button(
            top_buttons_frame, "ATEŞ ET", self._fire_button_callback, 
            bg_color=self.ui_colors['danger'], side=tk.LEFT, padx=5, fill=tk.X, expand=True
        )
        
        # Kalibrasyon butonu
        self.calibrate_button = self._create_rounded_button(
            top_buttons_frame, "KALİBRE ET", self._calibrate_motors_callback, 
            bg_color=self.ui_colors['accent'], side=tk.RIGHT, padx=5, fill=tk.X, expand=True
        )
        
        # Orta sıra butonları (Angajman kontrolleri)
        middle_buttons_frame = ttk.Frame(controls_frame, style='Panel.TFrame')
        middle_buttons_frame.pack(fill=tk.X, pady=5)
        
        # Angajman Onayla butonu (Mod 3'te aktif)
        self.confirm_button = self._create_rounded_button(
            middle_buttons_frame, "ANGAJMAN ONAYLA", self._confirm_engagement_callback, 
            bg_color=self.ui_colors['success'], side=tk.LEFT, padx=5, fill=tk.X, expand=True
        )
        
        # Angajman İptal butonu (Mod 3'te aktif)
        self.cancel_button = self._create_rounded_button(
            middle_buttons_frame, "ANGAJMAN İPTAL", self._cancel_engagement_callback, 
            bg_color=self.ui_colors['warning'], side=tk.RIGHT, padx=5, fill=tk.X, expand=True
        )
        
        # Alt sıra - Acil durum butonu
        bottom_buttons_frame = ttk.Frame(controls_frame, style='Panel.TFrame')
        bottom_buttons_frame.pack(fill=tk.X, pady=(15, 5))
        
        self.emergency_button = self._create_rounded_button(
            bottom_buttons_frame, "ACİL DURDURMA", self._emergency_stop_callback, 
            bg_color=self.ui_colors['danger'], height=50, padx=5, fill=tk.X, expand=True
        )
    
    def _create_rounded_button(self, parent, text, command, bg_color, height=40, **kwargs):
        """
        Yuvarlatılmış buton oluşturur.
        
        Args:
            parent: Üst widget
            text: Buton metni
            command: Tıklama olayı
            bg_color: Arka plan rengi
            height: Yükseklik
            **kwargs: Pack parametreleri
        
        Returns:
            dict: Buton bilgileri (canvas, text_id)
        """
        frame = ttk.Frame(parent, style='Panel.TFrame')
        frame.pack(**kwargs)
        
        canvas = tk.Canvas(frame, bg=self.ui_colors['panel'], height=height, 
                         highlightthickness=0)
        canvas.pack(fill=tk.X, expand=True)
        
        # Buton arka planı ve metin
        button_color = bg_color
        text_color = self.ui_colors['text']
        disabled = False  # Başlangıçta aktif
        
        def draw_button(color, outline_width=0, outline_color=None, shadow=True):
            canvas.delete("button")
            width = canvas.winfo_width()
            
            # 3D efekt için gölge
            if shadow:
                # Alt gölge - 3D efekti için
                shadow_color = self._adjust_color(color, 0.7)
                canvas.create_rounded_rectangle(3, 3, width-1, height, radius=10, 
                                            fill=shadow_color, tags="shadow")
            
            # Yuvarlatılmış buton çiz
            canvas.create_rounded_rectangle(0, 0, width-4, height-3, radius=10, 
                                         fill=color, outline=outline_color or "", 
                                         width=outline_width, tags="button")
            
            # Işık efekti - üst kısımda daha parlak bir çizgi
            if not disabled and shadow:
                highlight_color = self._adjust_color(color, 1.3)
                # Üst kenar parlaklığı
                canvas.create_line(5, 1, width-9, 1, 
                                fill=highlight_color, width=2, 
                                tags="button")
            
            # Metin ekle
            text_color_to_use = "#999999" if disabled else text_color
            text_id = canvas.create_text(width/2 - 2, height/2 - 1, text=text, 
                                      font=('Roboto', 11, 'bold'), fill=text_color_to_use, 
                                      tags="button")
            return text_id
        
        def update_button(event):
            width = event.width
            canvas.delete("all")
            text_color_to_use = "#999999" if disabled else text_color
            button_color_to_use = "#555555" if disabled else button_color
            
            # 3D efektleri ile buton çiz
            draw_button(button_color_to_use, shadow=not disabled)
        
        canvas.bind("<Configure>", update_button)
        
        # Tıklama olayı
        def on_click(event):
            if not disabled and command:
                # Tıklama efekti - basılmış gibi görünsün
                color = self._adjust_color(button_color, 0.85)
                canvas.delete("all")
                # Basılmış durumda gölge yok ve buton aşağı kaymış gibi
                draw_button(color, shadow=False)
                # Metni biraz kaydır
                canvas.move("button", 2, 2)
                
                canvas.update_idletasks()
                canvas.after(100, lambda: draw_button(button_color))
                command()
        
        # Hover olayları
        def on_enter(event):
            if not disabled:
                hover_color = self._adjust_color(button_color, 1.1)
                draw_button(hover_color, outline_width=1, outline_color=self.ui_colors['text'])
        
        def on_leave(event):
            if not disabled:
                draw_button(button_color)
        
        canvas.bind("<Button-1>", on_click)
        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        
        # Buton bilgisi
        button_info = {
            "canvas": canvas,
            "color": button_color,
            "is_disabled": lambda: disabled,
            "set_disabled": lambda state: setattr(button_info, 'disabled', state)
        }
        
        # Buton etkisizleştirme metodu
        def disable_button(state=True):
            nonlocal disabled
            disabled = state
            color = "#555555" if state else button_color
            width = canvas.winfo_width()
            canvas.delete("all")
            text_color_to_use = "#999999" if state else text_color
            # Gölge olmadan düz buton çiz
            draw_button(color, shadow=not state)
        
        button_info["disable"] = disable_button
        
        return button_info
    
    def _calibrate_motors_callback(self):
        """
        Motorları kalibre et butonuna basıldığında çağrılır.
        """
        self.logger.info("Motor kalibrasyonu başlatıldı")
        self._add_log_message("Gelişmiş motor kalibrasyonu başlatılıyor...", "INFO")
        
        # Kalibrasyon tipini belirleyen seçim kutusu
        cal_dialog = tk.Toplevel(self.ui_root)
        cal_dialog.title("Kalibrasyon Tipi Seçin")
        cal_dialog.geometry("300x150")
        cal_dialog.configure(bg="#212121")
        cal_dialog.grab_set()  # Modali yap
        
        # Kalibrasyon tipi
        cal_type = tk.IntVar(value=1)
        
        ttk.Label(cal_dialog, text="Kalibrasyon Tipini Seçin:", 
                 style='TLabel').pack(pady=10)
        
        ttk.Radiobutton(cal_dialog, text="Temel Kalibrasyon", 
                       variable=cal_type, value=1).pack(anchor=tk.W, padx=20)
        ttk.Radiobutton(cal_dialog, text="Gelişmiş Kalibrasyon", 
                       variable=cal_type, value=2).pack(anchor=tk.W, padx=20)
        
        def start_calibration():
            cal_type_val = cal_type.get()
            cal_dialog.destroy()
            
            if cal_type_val == 1:
                # Temel kalibrasyon
                if hasattr(self, 'safety') and hasattr(self.safety, 'motor_controller'):
                    result = self.safety.motor_controller.calibrate()
                    if result:
                        self._add_log_message("Motor kalibrasyonu başarıyla tamamlandı", "INFO")
                    else:
                        self._add_log_message("Motor kalibrasyonu başarısız oldu", "ERROR")
            else:
                # Gelişmiş kalibrasyon
                if hasattr(self, 'safety') and hasattr(self.safety, 'motor_controller'):
                    result = self.safety.motor_controller.advanced_calibration()
                    if result:
                        self._add_log_message("Gelişmiş kalibrasyon başarıyla tamamlandı", "INFO")
                    else:
                        self._add_log_message("Gelişmiş kalibrasyon başarısız oldu", "ERROR")
        
        ttk.Button(cal_dialog, text="Başlat", command=start_calibration).pack(pady=20)
    
    def _add_log_message(self, message, level):
        """
        Log mesajını görüntüle.
        
        Args:
            message: Log mesajı
            level: Log seviyesi (INFO, WARNING, ERROR, DEBUG, SUCCESS)
        """
        if not hasattr(self, 'log_text'):
            return
        
        # Zaman damgası ekle
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] - {message}"
            
        self.log_text.config(state=tk.NORMAL)
        
        # En son satırı görünür yap
        self.log_text.see(tk.END)
        
        # Son 100 satırı tut
        log_lines = self.log_text.get("1.0", tk.END).split("\n")
        if len(log_lines) > 100:
            self.log_text.delete("1.0", f"{len(log_lines) - 100}.0")
        
        # Yeni mesajı ekle
        self.log_text.insert(tk.END, formatted_message + "\n", level)
        
        # Mesajı belirgin yap ve birkaç saniye sonra normal haline getir
        if level in ["ERROR", "WARNING", "SUCCESS"]:
            # Son log'u belirgin yap
            tag_name = f"highlight_{int(time.time())}"
            last_line_start = self.log_text.index(f"end-2l")
            last_line_end = self.log_text.index(f"end-1l")
            
            # Özel vurgu stili oluştur
            self.log_text.tag_add(tag_name, last_line_start, last_line_end)
            self.log_text.tag_configure(tag_name, background="#3A3A3A")
            
            # Birkaç saniye sonra vurguyu kaldır
            self.ui_root.after(3000, lambda: self._remove_highlight(tag_name))
        
        # Son mesaja kaydır
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _remove_highlight(self, tag_name):
        """
        Log mesajından vurguyu kaldırır.
        
        Args:
            tag_name: Kaldırılacak tag adı
        """
        if hasattr(self, 'log_text'):
            self.log_text.tag_delete(tag_name)
    
    def _update_buttons(self):
        """
        Butonların durumunu günceller.
        """
        # Ateş butonu sadece Mod 1'de aktif
        if self.current_mode == 1:
            if hasattr(self.fire_button, "disable"):
                self.fire_button.disable(False)  # Etkinleştir
            else:
                self.fire_button["disable"](False)  # Dict versiyonu için
        else:
            if hasattr(self.fire_button, "disable"):
                self.fire_button.disable(True)  # Devre dışı bırak
            else:
                self.fire_button["disable"](True)  # Dict versiyonu için
        
        # Angajman butonları sadece Mod 3'te aktif
        if self.current_mode == 3:
            if hasattr(self.confirm_button, "disable"):
                self.confirm_button.disable(False)  # Etkinleştir
                self.cancel_button.disable(False)  # Etkinleştir
            else:
                self.confirm_button["disable"](False)  # Dict versiyonu için
                self.cancel_button["disable"](False)  # Dict versiyonu için
        else:
            if hasattr(self.confirm_button, "disable"):
                self.confirm_button.disable(True)  # Devre dışı bırak
                self.cancel_button.disable(True)  # Devre dışı bırak
            else:
                self.confirm_button["disable"](True)  # Dict versiyonu için
                self.cancel_button["disable"](True)  # Dict versiyonu için
    
    def _fire_button_callback(self):
        """
        Ateş butonuna basıldığında çağrılır.
        """
        # Önce butonu devre dışı bırak
        if hasattr(self.fire_button, "disable"):
            self.fire_button.disable(True)
        else:
            self.fire_button["disable"](True)
        
        # UI'ı güncellemek için bekle (butonun deaktif görünmesi için)
        self.ui_root.update_idletasks()
        
        # User input'u asenkron güncelle
        def _delayed_fire():
            self.user_input["fire"] = True
            self.logger.info("Ateş butonu basıldı")
            # Butonu tekrar aktifleştir
            if hasattr(self.fire_button, "disable"):
                self.fire_button.disable(False)
            else:
                self.fire_button["disable"](False)
        
        # Asenkron çalıştır
        self.ui_root.after(50, _delayed_fire)
    
    def _confirm_engagement_callback(self):
        """
        Angajman onay butonuna basıldığında çağrılır.
        """
        # Önce butonu devre dışı bırak
        if hasattr(self.confirm_button, "disable"):
            self.confirm_button.disable(True)
        else:
            self.confirm_button["disable"](True)
        
        # UI'ı güncellemek için bekle (butonun deaktif görünmesi için)
        self.ui_root.update_idletasks()
        
        # User input'u asenkron güncelle
        def _delayed_confirm():
            self.user_input["confirm_engagement"] = True
            self.logger.info("Angajman onaylandı")
            # Butonu tekrar aktifleştir
            if hasattr(self.confirm_button, "disable"):
                self.confirm_button.disable(False)
            else:
                self.confirm_button["disable"](False)
        
        # Asenkron çalıştır
        self.ui_root.after(50, _delayed_confirm)
    
    def _cancel_engagement_callback(self):
        """
        Angajman iptal butonuna basıldığında çağrılır.
        """
        # Önce butonu devre dışı bırak
        if hasattr(self.cancel_button, "disable"):
            self.cancel_button.disable(True)
        else:
            self.cancel_button["disable"](True)
        
        # UI'ı güncellemek için bekle (butonun deaktif görünmesi için)
        self.ui_root.update_idletasks()
        
        # User input'u asenkron güncelle
        def _delayed_cancel():
            self.user_input["cancel_engagement"] = True
            self.logger.info("Angajman iptal edildi")
            # Butonu tekrar aktifleştir
            if hasattr(self.cancel_button, "disable"):
                self.cancel_button.disable(False)
            else:
                self.cancel_button["disable"](False)
        
        # Asenkron çalıştır
        self.ui_root.after(50, _delayed_cancel)
    
    def _mode_changed(self, *args):
        """
        Mod değiştirildiğinde çağrılır.
        """
        # Mod değişikliği sırasında widget'ları devre dışı bırak
        if hasattr(self.fire_button, "disable"):
            self.fire_button.disable(True)
            self.confirm_button.disable(True)
            self.cancel_button.disable(True)
        else:
            self.fire_button["disable"](True)
            self.confirm_button["disable"](True)
            self.cancel_button["disable"](True)
        
        # UI'ı güncellemek için bekle
        self.ui_root.update_idletasks()
        
        # Mod değişikliğini asenkron yap
        def _delayed_mode_change():
            new_mode = self.mode_var.get()
            if new_mode != self.current_mode:
                # Mod değişim mesajını göster
                self.logger.info(f"Mod değiştiriliyor: {self.current_mode} → {new_mode}")
                
                # Modu anında değiştir
                self.current_mode = new_mode
                
                # Toggle butonlarını güncelle
                self._update_mode_toggles()
                
                # Butonları güncelle
                self._update_buttons()
                
                # Mod değişimini uygula
                self._apply_mode_change()
        
        # Asenkron çalıştır
        self.ui_root.after(100, _delayed_mode_change)
    
    def _update_mode_toggles(self):
        """
        Mod toggle butonlarını günceller.
        """
        # Tüm toggle butonları için
        for item in self.mode_labels:
            canvas = item["canvas"]
            mode_num = item["mode"]
            color = item["color"]
            
            # Aktif modu vurgula
            width = canvas.winfo_width()
            canvas.delete("button")
            
            # Buton rengini belirle
            button_color = color if mode_num == self.current_mode else self.ui_colors['panel']
            
            # Buton çiz
            canvas.create_rounded_rectangle(0, 0, width, 40, radius=10, 
                                         fill=button_color, outline="", tags="button")
            
            # Metin ekle - modern tarz için biraz daha büyük font
            font_weight = 'bold' if mode_num == self.current_mode else 'normal'
            canvas.create_text(width/2, 20, text=f"MOD {mode_num}", 
                            font=('Roboto', 11, font_weight), 
                            fill=self.ui_colors['text'], tags="button")
    
    def _apply_mode_change(self):
        """
        Mod değişimini uygular (optimize edilmiş).
        """
        # Mod bilgisini hızlıca güncelle
        mode_texts = {
            1: "MANUEL ATIŞ",
            2: "OTOMATİK ATIŞ",
            3: "ANGAJMAN"
        }
        self.mode_info_label.configure(text=mode_texts.get(self.current_mode, f"{self.current_mode}"))
            
        # Mod geçişi tamamlandı bildirimi
        self.logger.info(f"Mod {self.current_mode} aktif")
        self._add_log_message(f"Mod {self.current_mode} aktif", "SUCCESS")
    
    def _highlight_active_mode(self, active=True):
        """
        Aktif modu vurgular veya vurguyu kaldırır (optimize edilmiş).
        
        Args:
            active: True ise vurgula, False ise vurguyu kaldır
        """
        # Mode frame'i önbelleğe alma (ilk çağrıda hesapla ve sakla)
        if not hasattr(self, '_mode_frame_cache'):
            self._mode_frame_cache = None
            # Mode frame'i bul
            for child in self.ui_root.winfo_children():
                if isinstance(child, ttk.PanedWindow):
                    left_frame = child.pane(0)
                    for subchild in left_frame.winfo_children():
                        if isinstance(subchild, ttk.LabelFrame) and subchild.cget("text") == "Sistem Modu":
                            self._mode_frame_cache = subchild
                            break
                    if self._mode_frame_cache:
                        break
        
        # Frame bulunamadıysa çık
        if not self._mode_frame_cache:
            return
        
        # Tüm radiobutton düğmelerini tek döngüde güncelle
        for child in self._mode_frame_cache.winfo_children():
            if isinstance(child, ttk.Radiobutton):
                # Sadece sayı bölümünü ayıkla (performans için)
                mode_text = child.cget("text")
                mode_num = int(mode_text[4]) if len(mode_text) > 4 else 0
                
                # Stil güncelleme
                if mode_num == self.current_mode:
                    child.configure(style='Active.TRadiobutton')
                else:
                    child.configure(style='TRadiobutton')
    
    def _reset_user_input(self):
        """
        Kullanıcı girişini sıfırlar.
        """
        self.user_input = {
            "fire": False,
            "confirm_engagement": False,
            "cancel_engagement": False,
            "selected_target": None
        }
    
    def run(self):
        """
        Ana sistem döngüsünü çalıştırır.
        """
        self.running = True
        
        # Kullanıcı arayüzünü oluştur
        self._create_ui()
        
        # Güvenlik izlemeyi başlat
        self.safety.start_monitoring()
        
        self.logger.info("Sistem çalışıyor")
        
        # Ana döngü (tkinter event loop)
        try:
            self.ui_root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Kullanıcı tarafından durduruldu")
        finally:
            self.stop()
    
    def run_system_loop(self):
        """
        Sistem modu döngüsünü çalıştırır.
        Bu metod, tkinter event loop içerisinde periyodik olarak çağrılır.
        """
        # Ana işlemleri yapmıyorsa hemen dön (tıklama olayları sırasında hızlı cevap vermek için)
        if self.is_processing:
            self.ui_root.after(5, self.run_system_loop)
            return
        
        # Güvenlik kontrolü
        if not self.safety.is_system_safe():
            self.logger.warning("Sistem güvenli değil, modlar duraklatıldı")
            self.ui_root.after(50, self.run_system_loop)
            return
        
        # Zaman ölçümü başlat
        start_time = time.time()
        
        # Aktif modu çalıştır - hafif şekilde
        try:
            if self.current_mode == 1:
                # İşlem yapmadan önce çok kısa bir süre bekle (UI olaylarının işlenmesi için)
                self.is_processing = True
                self.ui_root.update_idletasks()
                self.is_processing = False
                
                self.mode1.run(self.user_input)
            elif self.current_mode == 2:
                # İşlem yapmadan önce çok kısa bir süre bekle (UI olaylarının işlenmesi için)
                self.is_processing = True
                self.ui_root.update_idletasks()
                self.is_processing = False
                
                self.mode2.run()
            elif self.current_mode == 3:
                # İşlem yapmadan önce çok kısa bir süre bekle (UI olaylarının işlenmesi için)
                self.is_processing = True
                self.ui_root.update_idletasks()
                self.is_processing = False
                
                self.mode3.run(self.user_input)
            
            # Kullanıcı girişini sıfırla
            self._reset_user_input()
            
            # İşlem süresini ölç
            processing_time = time.time() - start_time
            
            # Performans metrikleri (debug)
            if processing_time > 0.05:  # 50 ms'den uzun sürüyorsa log'la
                self.logger.debug(f"Mod {self.current_mode} döngüsü: {processing_time*1000:.1f} ms")
            
            # Tekrar çağır - işlem süresine göre gecikme ayarla
            delay = 20  # Varsayılan gecikme
            
            if processing_time < 0.01:  # 10 ms'den kısa ise
                delay = 20  # Normal gecikme
            elif processing_time > 0.1:  # 100 ms'den uzun ise
                delay = 5   # Çok az gecikme (işlem çok uzun sürdüyse)
            else:
                delay = max(5, int(20 - processing_time * 100))  # En az 5 ms bekle
            
            if self.running:
                self.ui_root.after(delay, self.run_system_loop)
            
        except Exception as e:
            self.logger.error(f"Sistem döngüsünde hata: {str(e)}")
            # Hata durumunda bile çalışmaya devam et
            if self.running:
                self.ui_root.after(100, self.run_system_loop)
    
    def stop(self):
        """
        Sistemi durdurur ve kaynakları serbest bırakır.
        """
        self.running = False
        
        # Güvenlik izlemeyi durdur
        self.safety.shutdown()
        
        # Kamerayı kapat
        if hasattr(self, 'camera'):
            self.camera.release()
        
        # Arduino bağlantısını kapat
        if hasattr(self, 'arduino'):
            self.arduino.close()
        
        self.logger.info("Sistem kapatıldı")

    def _emergency_stop_callback(self):
        """
        Acil durdurma butonuna basıldığında çağrılır.
        """
        # UI'ı dondurmamak için acil durdurma işlemini asenkron yap
        def _emergency_stop_async():
            if hasattr(self, 'arduino'):
                self.arduino.emergency_stop()
                self.logger.warning("ACİL DURDURMA butonu basıldı!")
            
        # Asenkron çalıştır
        self.ui_root.after(10, _emergency_stop_async)

    def _clear_logs(self):
        """
        Log mesajlarını temizler.
        """
        if hasattr(self, 'log_text'):
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete("1.0", tk.END)
            self.log_text.config(state=tk.DISABLED)
            self._add_log_message("Log ekranı temizlendi", "INFO")

    def _ui_focus_changed(self, is_focused):
        """
        UI odak değişikliğini yakalar.
        
        Args:
            is_focused: UI'a odaklanıldıysa True
        """
        self.is_ui_focused = is_focused
        if is_focused:
            # Odak kazanınca normal güncelleme
            self.ui_update_rate = 30  # ~30 FPS
        else:
            # Odaklanılmamışsa daha düşük güncelleme
            self.ui_update_rate = 100  # ~10 FPS
    
    def _update_cpu_usage(self):
        """
        CPU kullanımını günceller.
        """
        if not self.running:
            return
            
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.status_indicators["cpu"].configure(text=f"{cpu_percent:.1f}%")
            
            # CPU yüksekse UI güncelleme sıklığını azalt
            if cpu_percent > 80:
                self.ui_update_rate = 100  # Düşük güncelleme
            elif cpu_percent > 50:
                self.ui_update_rate = 50   # Orta güncelleme
            elif self.is_ui_focused:
                self.ui_update_rate = 30   # Normal güncelleme
        except Exception:
            # psutil kütüphanesi yüklü değilse sessizce geç
            pass
            
        self.ui_root.after(2000, self._update_cpu_usage)  # Her 2 saniyede kontrol et
        
    def _performance_mode_changed(self, *args):
        """
        Performans modu değiştirildiğinde çağrılır.
        """
        mode = self.performance_var.get()
        
        if mode == "Yüksek Hız":
            self.ui_update_rate = 100  # Daha az güncelleme
            # YOLO ayarlarını güncelle
            self.detector.confidence_threshold = 0.6  # Daha az hassas
            self._add_log_message("Yüksek Hız modu aktif", "INFO")
        elif mode == "Dengeli":
            self.ui_update_rate = 30   # Normal güncelleme
            # YOLO ayarlarını güncelle
            self.detector.confidence_threshold = 0.5  # Normal
            self._add_log_message("Dengeli mod aktif", "INFO")
        elif mode == "Yüksek Kalite":
            self.ui_update_rate = 30   # Normal güncelleme
            # YOLO ayarlarını güncelle
            self.detector.confidence_threshold = 0.4  # Daha hassas
            self._add_log_message("Yüksek Kalite modu aktif", "INFO")

    def _update_connection_status(self):
        """
        Bağlantı durum göstergelerini günceller.
        """
        # Kamera durumu
        if hasattr(self, 'camera') and hasattr(self.camera, 'is_working'):
            if self.camera.is_working():
                self.connection_status.configure(text="◉ KAMERA BAĞLI", foreground="#4CAF50")
            else:
                self.connection_status.configure(text="◉ KAMERA BAĞLANTISI YOK", foreground="#F44336")
        
        # Kayıt durumu (demo amaçlı)
        if hasattr(self, 'fps') and self.fps > 0:
            # Saniyede bir yanıp sönen kayıt göstergesi
            current_time = time.time()
            if int(current_time) % 2 == 0:
                self.recording_status.configure(text="◉ KAYIT YAPILIYOR", foreground="#E94560")
            else:
                self.recording_status.configure(text="◉ KAYIT YAPILIYOR", foreground="#999999")
        else:
            self.recording_status.configure(text="◉ KAYIT YAPILMIYOR", foreground="#999999")

    def _hover_mode(self, label, is_hover, mode):
        """
        Mod etiketine mouse hover efekti verir.
        
        Args:
            label: Etiket widget'ı
            is_hover: Mouse üzerinde ise True
            mode: Mod numarası (1-3)
        """
        # Aktif mod ise zaten vurgulanmış, değiştirme
        if mode == self.current_mode:
            return
        
        # Hover durumunu güncelle
        if is_hover:
            # Farklı bir font veya hafif renk değişikliği
            label.configure(font=('Roboto', 11, 'bold'))
            label.configure(foreground="#E0E0E0")  # Daha parlak metin
        else:
            # Normal haline geri dön
            label.configure(font=('Roboto', 11))
            label.configure(foreground="#F5F5F5")  # Normal metin rengi

    def _create_camera_panel(self, parent):
        """
        Kamera görüntüsü ve hedef tespiti için panel oluşturur.
        
        Args:
            parent: Üst widget
        """
        # Kamera paneli çerçevesi
        camera_frame = ttk.Frame(parent, style='TFrame')
        camera_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10, 5))
        
        # Kamera başlık çerçevesi
        camera_header = ttk.Frame(camera_frame, style='TFrame')
        camera_header.pack(fill=tk.X, pady=(0, 5))
        
        # Kamera başlığı
        ttk.Label(camera_header, text="KAMERA GÖRÜNTÜSÜ & HEDEF TESPİTİ", 
                 style='Header.TLabel').pack(side=tk.LEFT, padx=15)
        
        # Durum göstergeleri - sağda
        status_frame = ttk.Frame(camera_header, style='TFrame')
        status_frame.pack(side=tk.RIGHT, padx=15)
        
        # Kamera durum göstergesi
        self.connection_status = ttk.Label(status_frame, text="◉ KAMERA BAĞLANIYOR...", 
                                         foreground="#FFB300", font=('Roboto', 10))
        self.connection_status.pack(side=tk.RIGHT, padx=10)
        
        # Kayıt durumu
        self.recording_status = ttk.Label(status_frame, text="◉ KAYIT YAPILMIYOR", 
                                        foreground="#999999", font=('Roboto', 10))
        self.recording_status.pack(side=tk.RIGHT, padx=10)
        
        # Kamera görüntü alanı için çerçeve
        frame_holder = ttk.Frame(camera_frame, style='Panel.TFrame')
        frame_holder.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        
        # Canvas ile yuvarlatılmış görüntü alanı
        self.camera_canvas = tk.Canvas(frame_holder, bg=self.ui_colors['indicator'], 
                                     highlightthickness=0)
        self.camera_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def draw_rounded_camera_frame(event):
            width = event.width
            height = event.height
            self.camera_canvas.delete("camera_frame")
            self.camera_canvas.create_rounded_rectangle(0, 0, width, height, radius=15, 
                                                   fill=self.ui_colors['indicator'], 
                                                   outline="", tags="camera_frame")
        
        self.camera_canvas.bind("<Configure>", draw_rounded_camera_frame)
        
        # Boş kamera görüntüsü
        empty_img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2_img = cv2.putText(empty_img, "HSS - Kamera Görüntüsü Bekleniyor...", (120, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        
        # PIL için rengi BGR'den RGB'ye dönüştür
        cv2_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(cv2_img)
        self.current_photo = ImageTk.PhotoImage(image=pil_img)
        
        # Görüntü göstericisi
        self.cam_image_id = self.camera_canvas.create_image(0, 0, image=self.current_photo, 
                                                       anchor=tk.NW, tags="camera_image")
        
        # Görüntü üzerine tıklama olayı (hedef seçimi için)
        def on_camera_click(event):
            if self.current_mode == 3:  # Sadece angajman modunda
                # Gerçek kamera koordinatlarına dönüştür
                # (Canvas boyutu ve kamera çözünürlüğü farklı olabilir)
                canvas_width = self.camera_canvas.winfo_width()
                canvas_height = self.camera_canvas.winfo_height()
                
                # Orijinal kamera çözünürlüğüne oranla
                x_ratio = CAMERA_WIDTH / canvas_width
                y_ratio = CAMERA_HEIGHT / canvas_height
                
                real_x = int(event.x * x_ratio) 
                real_y = int(event.y * y_ratio)
                
                # Kullanıcının seçtiği hedef
                self.user_input["selected_target"] = (real_x, real_y)
                
                # Seçilen noktayı göster
                self._add_log_message(f"Hedef seçildi: ({real_x}, {real_y})", "INFO")
        
        self.camera_canvas.bind("<Button-1>", on_camera_click)
        
        # FPS göstergesi
        self.fps_label = ttk.Label(camera_frame, text="FPS: --", style='Info.TLabel',
                                background=self.ui_colors['bg'], font=('Roboto Mono', 10))
        self.fps_label.pack(side=tk.RIGHT, anchor=tk.SE, padx=15, pady=5)
    
    def _create_target_panel(self, parent):
        """
        Hedef takip bilgileri için panel oluşturur.
        
        Args:
            parent: Üst widget
        """
        # Ana çerçeve
        target_frame = ttk.Frame(parent, style='TFrame')
        target_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Hedef bilgisi paneli
        self._create_rounded_frame(target_frame, "HEDEF TAKİP BİLGİSİ", self._create_target_info, 
                                padx=5, pady=5)
    
    def _create_target_info(self, parent):
        """
        Hedef bilgisi içeriğini oluşturur.
        
        Args:
            parent: Üst widget
        """
        # Hedef bilgisi göstergeleri için ana çerçeve
        target_info_frame = ttk.Frame(parent, style='Panel.TFrame')
        target_info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 3 sütunlu düzen
        info_grid = ttk.Frame(target_info_frame, style='Panel.TFrame')
        info_grid.pack(fill=tk.X, expand=True)
        
        # Hedef bilgisi göstergeleri
        target_infos = [
            {"name": "konum_x", "label": "Hedef X:", "value": "--", "unit": "px"},
            {"name": "konum_y", "label": "Hedef Y:", "value": "--", "unit": "px"},
            {"name": "uzaklik", "label": "Uzaklık:", "value": "--", "unit": "m"},
            {"name": "genislik", "label": "Genişlik:", "value": "--", "unit": "px"},
            {"name": "yukseklik", "label": "Yükseklik:", "value": "--", "unit": "px"},
            {"name": "aci", "label": "Açı:", "value": "--", "unit": "°"},
            {"name": "hedef_turu", "label": "Hedef Türü:", "value": "--", "unit": ""},
            {"name": "kilitlenme", "label": "Kilitlenme:", "value": "YOK", "unit": ""},
            {"name": "angajman", "label": "Angajman:", "value": "PASİF", "unit": ""}
        ]
        
        # Grid'e hedef bilgilerini yerleştir
        for i, info in enumerate(target_infos):
            row = i // 3
            col = i % 3
            
            # Her bilgi için çerçeve
            cell_frame = ttk.Frame(info_grid, style='Panel.TFrame')
            cell_frame.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            
            # İndikatör
            indicator_frame = ttk.Frame(cell_frame, style='Indicator.TFrame')
            indicator_frame.pack(fill=tk.X, expand=True, padx=0, pady=0)
            
            # Etiket ve değer
            label = ttk.Label(indicator_frame, text=info["label"], style='Indicator.TLabel')
            label.pack(side=tk.LEFT, padx=5, pady=3)
            
            # Değer göstergesi
            value_label = ttk.Label(indicator_frame, 
                                  text=f"{info['value']} {info['unit']}", 
                                  style='Value.TLabel')
            value_label.pack(side=tk.RIGHT, padx=5, pady=3)
            
            # Değeri sakla
            self.status_indicators[info["name"]] = value_label
        
        # Kilit durumu için özel LED gösterge paneli
        led_frame = ttk.Frame(target_info_frame, style='Panel.TFrame')
        led_frame.pack(fill=tk.X, expand=True, padx=10, pady=(15, 5))
        
        # LED göstergeleri
        led_infos = [
            {"name": "kilitli", "label": "KİLİTLİ", "color": self.ui_colors['success'], "active": False},
            {"name": "izlemede", "label": "İZLEMEDE", "color": self.ui_colors['info'], "active": True},
            {"name": "tespit", "label": "TESPİT", "color": self.ui_colors['warning'], "active": True}
        ]
        
        # LED çerçevesi grid düzeni
        for i, led in enumerate(led_infos):
            # LED göstergesi çerçevesi
            led_item = ttk.Frame(led_frame, style='Panel.TFrame')
            led_item.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=10)
            
            # LED gösterge led
            led_indicator = tk.Canvas(led_item, width=15, height=15, 
                                    bg=self.ui_colors['panel'], highlightthickness=0)
            led_indicator.pack(side=tk.LEFT, padx=5)
            
            # LED çember çiz
            color = led["color"] if led["active"] else "#555555"
            led_id = led_indicator.create_oval(0, 0, 15, 15, fill=color, outline=color)
            
            # LED etiket
            led_label = ttk.Label(led_item, text=led["label"], style='Status.TLabel')
            led_label.pack(side=tk.LEFT, padx=5)
            
            # LED durumunu sakla
            self.status_leds[led["name"]] = {"canvas": led_indicator, "id": led_id}
    
    def _create_info_panel(self, parent):
        """
        Alt bilgi paneli oluşturur.
        
        Args:
            parent: Üst widget
        """
        # Bilgi paneli çerçevesi
        info_frame = ttk.Frame(parent, style='TFrame')
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # İki sütunlu düzen: sol ve sağ kısımlar
        left_info = ttk.Frame(info_frame, style='TFrame')
        left_info.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Durum bilgileri paneli
        self._create_rounded_frame(left_info, "SİSTEM BİLGİLERİ", self._create_status_info, 
                                padx=5, pady=5)
    
    def _create_status_info(self, parent):
        """
        Durum bilgileri içeriğini oluşturur.
        
        Args:
            parent: Üst widget
        """
        status_info_frame = ttk.Frame(parent, style='Panel.TFrame')
        status_info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 2 sütunlu grid düzen
        info_grid = ttk.Frame(status_info_frame, style='Panel.TFrame')
        info_grid.pack(fill=tk.X, expand=True)
        
        # Durum göstergeleri
        status_infos = [
            {"name": "mode", "label": "Aktif Mod:", "value": "MANUEL ATIŞ", "color": "info"},
            {"name": "cpu", "label": "CPU Kullanımı:", "value": "--", "color": "info"},
            {"name": "fps", "label": "Kamera FPS:", "value": "--", "color": "info"},
            {"name": "yolo_fps", "label": "YOLO FPS:", "value": "--", "color": "info"},
            {"name": "motor_x", "label": "Motor X:", "value": "--", "color": "info"},
            {"name": "motor_y", "label": "Motor Y:", "value": "--", "color": "info"}
        ]
        
        # Grid'e durum bilgilerini yerleştir
        for i, info in enumerate(status_infos):
            row = i // 2
            col = i % 2
            
            # Her bilgi için çerçeve
            cell_frame = ttk.Frame(info_grid, style='Panel.TFrame')
            cell_frame.grid(row=row, column=col, padx=10, pady=5, sticky="w")
            
            # İndikatör
            indicator_frame = ttk.Frame(cell_frame, style='Indicator.TFrame')
            indicator_frame.pack(fill=tk.X, expand=True, padx=0, pady=0)
            
            # Etiket ve değer
            label = ttk.Label(indicator_frame, text=info["label"], style='Indicator.TLabel')
            label.pack(side=tk.LEFT, padx=5, pady=3)
            
            # Değer göstergesi (renk ile)
            color_style = f"{info['color'].capitalize()}.TLabel" if info['color'] in ["info", "warning", "success", "danger"] else "Info.TLabel"
            value_label = ttk.Label(indicator_frame, text=info["value"], style=color_style)
            value_label.pack(side=tk.RIGHT, padx=5, pady=3)
            
            # Referansı sakla
            self.status_indicators[info["name"]] = value_label
        
        # Mod bilgisi için özel referans
        self.mode_info_label = self.status_indicators["mode"]
    
    def _create_status_section(self, parent):
        """
        Durum ve uyarı göstergeleri bölümünü oluşturur.
        
        Args:
            parent: Üst widget
        """
        # Ana çerçeve
        status_frame = ttk.Frame(parent, style='Panel.TFrame')
        status_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Bağlantı durumu
        conn_frame = ttk.Frame(status_frame, style='Panel.TFrame')
        conn_frame.pack(fill=tk.X, expand=False, pady=(0, 10))
        
        # Bağlantı durumu başlığı
        ttk.Label(conn_frame, text="BAĞLANTI DURUMU:", 
                 style='Subheader.TLabel').pack(anchor=tk.W, padx=5, pady=(5, 10))
        
        # Bağlantı göstergeleri
        status_items = [
            {"name": "kamera", "label": "Kamera:", "value": "BAĞLI", "color": "success"},
            {"name": "arduino", "label": "Arduino:", "value": "BAĞLI", "color": "success"},
            {"name": "atis", "label": "Atış Sistemi:", "value": "HAZIR", "color": "success"}
        ]
        
        # LED durum göstergeleri
        status_grid = ttk.Frame(conn_frame, style='Panel.TFrame')
        status_grid.pack(fill=tk.X, expand=True, padx=5)
        
        for i, item in enumerate(status_items):
            # Her durum için bir çerçeve
            item_frame = ttk.Frame(status_grid, style='Panel.TFrame')
            item_frame.pack(fill=tk.X, pady=3)
            
            # LED göstergesi (canvas ile yuvarlak)
            led_canvas = tk.Canvas(item_frame, width=15, height=15, 
                                 bg=self.ui_colors['panel'], highlightthickness=0)
            led_canvas.pack(side=tk.LEFT, padx=5)
            
            # LED rengi
            color_map = {
                "success": self.ui_colors['success'],
                "warning": self.ui_colors['warning'],
                "danger": self.ui_colors['danger'],
                "info": self.ui_colors['info']
            }
            led_color = color_map.get(item["color"], "#999999")
            
            # Yuvarlak LED çiz
            led_id = led_canvas.create_oval(2, 2, 13, 13, fill=led_color, outline="")
            
            # Durum etiketi
            label = ttk.Label(item_frame, text=f"{item['label']} {item['value']}", 
                            style='Status.TLabel')
            label.pack(side=tk.LEFT, padx=10)
            
            # Referansı sakla
            self.status_leds[item["name"]] = {"canvas": led_canvas, "id": led_id}
            
        # Sistem durumu
        sys_frame = ttk.Frame(status_frame, style='Panel.TFrame')
        sys_frame.pack(fill=tk.X, expand=False, pady=(10, 10))
        
        # Sistem durumu başlığı
        ttk.Label(sys_frame, text="SİSTEM DURUMU:", 
                 style='Subheader.TLabel').pack(anchor=tk.W, padx=5, pady=(5, 10))
        
        # Sistem durumu göstergeleri - gri arka planlı
        sys_status_frame = ttk.Frame(sys_frame, style='Indicator.TFrame')
        sys_status_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Sistem durumu etiketi (büyük ve belirgin)
        system_status = ttk.Label(sys_status_frame, text="SİSTEM AKTİF", foreground="#4CAF50",
                                font=('Roboto', 14, 'bold'), padding=10)
        system_status.pack(fill=tk.X, expand=True)
        
        # Referans sakla
        self.system_status_label = system_status
        
        # Güvenlik durumu
        safety_frame = ttk.Frame(status_frame, style='Panel.TFrame')
        safety_frame.pack(fill=tk.X, expand=False, pady=(10, 5))
        
        # Güvenlik durumu başlığı
        ttk.Label(safety_frame, text="GÜVENLİK DURUMU:", 
                 style='Subheader.TLabel').pack(anchor=tk.W, padx=5, pady=(5, 10))
        
        # Güvenlik durumu göstergeleri - butonlar olarak
        safety_buttons_frame = ttk.Frame(safety_frame, style='Panel.TFrame')
        safety_buttons_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Güvenlik durum butonları
        self._create_rounded_button(
            safety_buttons_frame, "GÜVENLİK AKTİF", None, 
            bg_color=self.ui_colors['success'], 
            padx=5, fill=tk.X, expand=True
        )
        
        # Uyarı paneli
        warning_frame = ttk.Frame(status_frame, style='Panel.TFrame')
        warning_frame.pack(fill=tk.X, expand=True, pady=(10, 5))
        
        # Uyarılar başlığı
        ttk.Label(warning_frame, text="UYARILAR:", 
                 style='Subheader.TLabel').pack(anchor=tk.W, padx=5, pady=(5, 5))
        
        # Uyarı listesi için çerçeve
        warnings_list_frame = ttk.Frame(warning_frame, style='Indicator.TFrame')
        warnings_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Varsayılan uyarı - hiç uyarı yok
        self.warnings_label = ttk.Label(warnings_list_frame, text="Aktif uyarı bulunmuyor",
                                      foreground=self.ui_colors['success'], padding=10,
                                      justify=tk.LEFT, wraplength=250)
        self.warnings_label.pack(fill=tk.X, expand=True)
        
        # Aktif uyarıları saklamak için liste
        self.active_warnings = []
    
    def _create_log_panel(self, parent):
        """
        Log kaydı paneli oluşturur.
        
        Args:
            parent: Üst widget
        """
        # Log paneli çerçevesi
        log_frame = ttk.Frame(parent, style='TFrame')
        log_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        # Yuvarlatılmış kenarlar ile log paneli
        log_canvas_frame = ttk.Frame(log_frame, style='TFrame')
        log_canvas_frame.pack(fill=tk.X, expand=True)
        
        # Başlık
        ttk.Label(log_canvas_frame, text="SİSTEM LOGARI", 
                 style='TLabelframe.Label').pack(anchor=tk.NW, padx=15, pady=(0, 5))
        
        # Log alanı için canvas
        log_canvas = tk.Canvas(log_canvas_frame, bg=self.ui_colors['panel'], 
                             highlightthickness=0, height=150)
        log_canvas.pack(fill=tk.X, expand=True, padx=5, pady=5)
        
        # Yuvarlatılmış dikdörtgen çiz
        def draw_rounded_log(event):
            width = event.width
            height = event.height
            log_canvas.delete("log_rect")
            log_canvas.create_rounded_rectangle(0, 0, width, height, radius=15, 
                                             fill=self.ui_colors['panel'], outline="", 
                                             tags="log_rect")
            log_canvas.tag_lower("log_rect")
        
        log_canvas.bind("<Configure>", draw_rounded_log)
        
        # İçerik çerçevesi
        log_content = ttk.Frame(log_canvas, style='Panel.TFrame')
        log_canvas.create_window(5, 5, anchor=tk.NW, window=log_content, 
                               tags="log_content", width=800, height=140)
        
        def update_log_window(event):
            width = event.width
            height = event.height
            log_canvas.itemconfig("log_content", width=width-10, height=height-10)
        
        log_canvas.bind("<Configure>", lambda e: (draw_rounded_log(e), update_log_window(e)))
        
        # Kaydırma çubuğu ile metin alanı
        log_scrollbar = ttk.Scrollbar(log_content)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Log text widget
        self.log_text = tk.Text(log_content, height=8, width=80, bg=self.ui_colors['indicator'],
                              fg=self.ui_colors['text'], bd=0, font=('Roboto Mono', 9),
                              yscrollcommand=log_scrollbar.set)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.config(command=self.log_text.yview)
        
        # Log seviyelerine göre renklendirme etiketleri
        self.log_text.tag_configure("INFO", foreground="#3B82F6")  # Mavi
        self.log_text.tag_configure("WARNING", foreground="#F59E0B")  # Sarı
        self.log_text.tag_configure("ERROR", foreground="#EF4444")  # Kırmızı
        self.log_text.tag_configure("SUCCESS", foreground="#10B981")  # Yeşil
        self.log_text.tag_configure("DEBUG", foreground="#94A3B8")  # Gri
        
        # Başlangıçta devre dışı bırak (salt okunur)
        self.log_text.config(state=tk.DISABLED)
        
        # Temizleme butonu
        clear_log_button = ttk.Button(log_content, text="Temizle", command=self._clear_logs)
        clear_log_button.place(relx=1.0, rely=0.0, anchor=tk.NE, x=-20, y=5)
        
        # Hoşgeldin mesajı
        self._add_log_message("HSS sistemi başlatıldı", "INFO")
        self._add_log_message("Kamera bağlantısı bekleniyor...", "INFO")
    
    def _update_ui(self):
        """
        Kullanıcı arayüzü öğelerini günceller.
        """
        if not self.running:
            return
            
        # Kamera çerçevesini güncelle
        try:
            if hasattr(self, 'camera'):
                ret, frame = self.camera.get_frame()
                
                if ret and frame is not None:
                    # Performans ayarı - düşük performans modunda YOLO'yu daha az sıklıkla çalıştır
                    self.yolo_process_frame_count += 1
                    process_frame = False
                    
                    # Performans moduna göre YOLO işleme sıklığını ayarla
                    perf_mode = self.performance_var.get()
                    skip_frames = 4  # Varsayılan: her 4 karede bir (daha iyi performans)
                    
                    if perf_mode == "Yüksek Hız":
                        skip_frames = 6  # Her 6 karede bir (maksimum performans)
                    elif perf_mode == "Yüksek Kalite": 
                        skip_frames = 2  # Her 2 karede bir (daha iyi kalite)
                    
                    # Frame atlama kontrolü - config'deki değer ile çarparak daha fazla atlama
                    process_frame = (self.yolo_process_frame_count % (skip_frames * YOLO_PROCESS_EVERY_N_FRAME) == 0)
                    
                    # YOLO tespiti (belirli periyodlarla)
                    if process_frame and self.detector:
                        # YOLO tespitleri
                        detections = self.detector.detect(frame)
                        
                        # Tespit edilen nesneleri çiz
                        if len(detections) > 0:
                            for detection in detections:
                                # Tespit edilen nesnenin kutu koordinatları
                                x, y, w, h = detection["box"]
                                
                                # Tespit türü ve güven değeri
                                label = detection.get("class", "Nesne")
                                confidence = detection.get("confidence", 0)
                                
                                # Kutu rengi - Mavi
                                color = (255, 0, 0) if label == "mavi_balon" else (0, 0, 255)
                                
                                # Çerçeve çiz
                                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                                
                                # Etiket metni
                                text = f"{label}: {confidence:.2f}"
                                
                                # Metin rengi (arka plan için zıt renk)
                                text_color = (255, 255, 255)
                                
                                # Etiket için arka plan boyutu
                                (text_width, text_height), _ = cv2.getTextSize(
                                    text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                                
                                # Etiket arka planı
                                cv2.rectangle(frame, (x, y - 20), (x + text_width, y), color, -1)
                                
                                # Etiket metni
                                cv2.putText(frame, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                                          0.5, text_color, 1)
                    
                    # PIL için görüntüyü BGR'den RGB'ye dönüştür
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Kamera canvas'ın boyutunu al
                    canvas_width = self.camera_canvas.winfo_width()
                    canvas_height = self.camera_canvas.winfo_height()
                    
                    # Statik değişkenleri tanımla - her kare için hesaplama yapmamak için
                    if not hasattr(self, 'last_canvas_size') or self.last_canvas_size != (canvas_width, canvas_height):
                        self.last_canvas_size = (canvas_width, canvas_height)
                        self.resize_needed = True
                    else:
                        # Canvas boyutu değişmediyse boyutlandırmayı atla (performans için)
                        self.resize_needed = False
                    
                    if canvas_width > 1 and canvas_height > 1 and self.resize_needed:  # Geçerli boyut kontrolü
                        # Oranı koru
                        img_height, img_width = frame.shape[:2]
                        aspect_ratio = img_width / img_height
                        
                        # Canvas boyutuna sığdır (en-boy oranını koru)
                        if canvas_width / canvas_height > aspect_ratio:
                            # Canvas daha geniş, yüksekliğe göre ayarla
                            new_height = canvas_height
                            new_width = int(new_height * aspect_ratio)
                        else:
                            # Canvas daha dar, genişliğe göre ayarla
                            new_width = canvas_width
                            new_height = int(new_width / aspect_ratio)
                        
                        # Yeni boyutları sakla
                        self.last_resize_dims = (new_width, new_height)
                    elif not hasattr(self, 'last_resize_dims'):
                        # İlk çalıştırma için varsayılan değerler
                        self.last_resize_dims = (canvas_width, canvas_height)
                    
                    # Görüntüyü yeniden boyutlandır (performans için LANCZOS yerine NEAREST kullan)
                    pil_img = Image.fromarray(rgb_frame)
                    pil_img = pil_img.resize(self.last_resize_dims, Image.NEAREST)
                    
                    # ImageTk ile görüntüyü güncelle
                    self.current_photo = ImageTk.PhotoImage(image=pil_img)
                    
                    # Canvas'ı güncelle
                    self.camera_canvas.delete("camera_image")
                    self.cam_image_id = self.camera_canvas.create_image(
                        canvas_width // 2, canvas_height // 2, 
                        image=self.current_photo, anchor=tk.CENTER, tags="camera_image")
                    
                    # FPS hesapla
                    current_time = time.time()
                    if current_time - self.last_frame_time >= 1.0:  # Her saniye güncelle
                        self.fps = self.frame_count
                        self.frame_count = 0
                        self.last_frame_time = current_time
                        
                        # FPS etiketini güncelle
                        self.fps_label.configure(text=f"FPS: {self.fps}")
                        
                        # CPU kullanım etiketini güncelle (eğer psutil yüklü ise)
                        if "cpu" in self.status_indicators:
                            try:
                                import psutil
                                cpu_percent = psutil.cpu_percent(interval=None)
                                self.status_indicators["cpu"].configure(text=f"{cpu_percent:.1f}%")
                            except (ImportError, Exception):
                                pass
                        
                        # Kamera ve kayıt durumunu güncelle
                        self._update_connection_status()
                    
                    self.frame_count += 1
                
                # Kamera ve YOLO FPS değerlerini güncelle
                if "fps" in self.status_indicators:
                    self.status_indicators["fps"].configure(text=f"{self.fps}")
                
                if "yolo_fps" in self.status_indicators:
                    yolo_fps = self.fps // skip_frames
                    self.status_indicators["yolo_fps"].configure(text=f"{yolo_fps}")
            
            # Motor değerlerini güncelle
            if self.arduino and self.arduino.is_connected():
                motor_x = self.arduino.get_servo_position(1)
                motor_y = self.arduino.get_servo_position(2)
                
                if "motor_x" in self.status_indicators:
                    self.status_indicators["motor_x"].configure(text=f"{motor_x}°")
                
                if "motor_y" in self.status_indicators:
                    self.status_indicators["motor_y"].configure(text=f"{motor_y}°")
        
        except Exception as e:
            logging.error(f"UI güncellerken hata: {str(e)}")
        
        # Modu güncelle
        if "mode" in self.status_indicators:
            mode_texts = {
                1: "MANUEL ATIŞ",
                2: "OTOMATİK ATIŞ", 
                3: "ANGAJMAN"
            }
            mode_text = mode_texts.get(self.current_mode, str(self.current_mode))
            self.status_indicators["mode"].configure(text=mode_text)
        
        # UI üzerindeki işlemler çok uzun sürüyorsa
        self.ui_root.after(self.ui_update_rate, self._update_ui)
    
    def _adjust_color(self, hex_color, factor):
        """
        Rengi parlatma/karartma faktörüne göre ayarlar.
        
        Args:
            hex_color: Hex renk kodu (#RRGGBB)
            factor: Parlatma/karartma çarpanı (>1 parlatır, <1 karartır)
        
        Returns:
            str: Ayarlanmış hex renk kodu
        """
        # Hex kodunu RGB'ye dönüştür
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        
        # Renkleri faktöre göre ayarla
        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))
        
        # Yeni hex kodunu döndür
        return f"#{r:02x}{g:02x}{b:02x}"

# Özel Log işleyicisi - UI'da göstermek için
class LogHandler(logging.Handler):
    """
    UI'da log mesajlarını göstermek için özel handler.
    """
    def __init__(self, ui_instance):
        super().__init__()
        self.ui = ui_instance
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', '%H:%M:%S'))
    
    def emit(self, record):
        log_entry = self.format(record)
        level = record.levelname
        
        # Ana thread'de UI güncellemesi yap
        self.ui.ui_root.after(0, lambda: self.ui._add_log_message(log_entry, level))

def main():
    """
    Ana program başlangıç noktası.
    """
    parser = argparse.ArgumentParser(description="Hava Savunma Sistemi")
    parser.add_argument("--headless", action="store_true", help="Arayüzsüz modda çalıştır")
    args = parser.parse_args()
    
    # Hava Savunma Sistemi nesnesini oluştur
    system = HSSSystem()
    
    if args.headless:
        # Arayüzsüz mod (konsol tabanlı)
        system.running = True
        
        # Güvenlik izlemeyi başlat
        system.safety.start_monitoring()
        
        # İşlev modlarını başlat
        system.logger.info("Sistem arayüzsüz modda çalışıyor")
        
        try:
            # Ana döngü
            system.current_mode = 1  # Varsayılan olarak mod 1 ile başla
            
            while system.running:
                # Kamera görüntüsünü al
                ret, frame = system.camera.get_frame()
                
                if ret and frame is not None:
                    # YOLO tespitleri
                    detections = system.detector.detect(frame)
                    detections = system.detector.classify_balloons(frame, detections)
                    
                    # Aktif modu çalıştır
                    if system.current_mode == 1:
                        system.mode1.run({"fire": False})  # Manuel atış yok
                    elif system.current_mode == 2:
                        system.mode2.run()
                    
                # Kısa bekleme
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            system.logger.info("Kullanıcı tarafından durduruldu")
        finally:
            system.stop()
    else:
        try:
            # PyQt5 tabanlı arayüz modunu kullan (eğer varsa)
            try:
                from HSS.gui.qt_interface import run_qt_interface
                system.logger.info("PyQt5 arayüzü başlatılıyor...")
                run_qt_interface(system)
            except ImportError:
                system.logger.warning("PyQt5 arayüzü bulunamadı, Tkinter arayüzüne geçiliyor...")
                # İçe aktarma başarısız olursa Tkinter arayüzüne geri dön
                system.run()  # Tkinter arayüzünü başlat
        finally:
            system.stop()

if __name__ == "__main__":
    main() 