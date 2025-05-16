"""
Mod 1: Otomatik Takip, Manuel Ates.

Bu modda:
1. Tüm balonlar (kırmızı/mavi) otomatik olarak tespit edilir
2. En yakın balon hedef olarak seçilir ve takip edilir
3. Atış komutu manuel olarak kullanıcıdan beklenir
"""

import time
import logging
import cv2
import numpy as np
from typing import Dict, Any, Tuple

class Mode1:
    """
    Mod 1: Otomatik Takip, Manuel Ates modu.
    """
    
    def __init__(self, camera, detector, arduino_comm, safety_monitor):
        """
        Mode1 sınıfını başlatır.
        
        Args:
            camera: Kamera nesnesi
            detector: YoloDetector nesnesi
            arduino_comm: ArduinoComm nesnesi
            safety_monitor: SafetyMonitor nesnesi
        """
        self.camera = camera
        self.detector = detector
        self.arduino = arduino_comm
        self.safety = safety_monitor
        
        # Motor ve lazer kontrol nesnelerini al
        self.motor_controller = safety_monitor.motor_controller
        self.laser_controller = safety_monitor.laser_controller
        
        # Mod durumu
        self.is_running = False
        self.start_time = 0
        self.timeout = 300  # 5 dakika
        
        # Hedef takibi
        self.current_target = None
        self.target_locked = False
        
        # Görüntü işleme parametreleri
        self.frame_center = (320, 240)  # Varsayılan (640x480 için)
        
        # Logger
        self.logger = logging.getLogger("Mode1")
    
    def run(self, user_input: Dict = None):
        """
        Mod 1'i çalıştırır.
        
        Args:
            user_input: Kullanıcıdan gelen giriş
        """
        if not self.is_running:
            self._start()
        
        # Kamera çalışıyor mu kontrol et
        if not self.camera.is_working():
            self.logger.error("Kamera çalışmıyor, mod durduruluyor")
            self._stop()
            return
        
        # Görüntü al
        ret, frame = self.camera.get_frame()
        if not ret or frame is None:
            return
        
        # Görüntü boyutlarını al
        height, width, _ = frame.shape
        self.frame_center = (width // 2, height // 2)
        
        # Hedefleri tespit et
        detections = self.detector.detect(frame)
        
        # Balon renk sınıflandırması
        detections = self.detector.classify_balloons(frame, detections)
        
        # Tüm balonlar arasında en yakın olanı bul
        balloon_detections = [d for d in detections if "balloon" in d["class_name"]]
        target = self.detector.find_closest_target(balloon_detections, self.frame_center)
        
        # Hedef varsa takip et
        if target:
            self.current_target = target
            self._track_target(target)
        else:
            self.current_target = None
            self.target_locked = False
        
        # Görüntüye tespitleri çiz
        frame_with_detections = self.detector.draw_detections(frame, detections)
        
        # Kullanıcı girişi varsa ve ateş komutu geldi mi kontrol et
        if user_input and user_input.get("fire") and self.target_locked:
            self._fire_at_target()
        
        # Zaman aşımı kontrolü
        if self.start_time > 0 and time.time() - self.start_time > self.timeout:
            self.logger.info("Mod 1 zaman aşımı, durduruluyor")
            self._stop()
    
    def _start(self):
        """
        Mod 1'i başlatır.
        """
        self.is_running = True
        self.start_time = time.time()
        self.target_locked = False
        
        # Kamerayı başlat (eğer başlatılmamışsa)
        if not self.camera.is_working():
            self.camera.initialize()
        
        # YOLO dedektörünü başlat
        self.detector.initialize()
        
        # Motorları kalibre et
        self.motor_controller.calibrate()
        
        self.logger.info("Mod 1 başlatıldı: Otomatik Takip, Manuel Ates")
    
    def _stop(self):
        """
        Mod 1'i durdurur.
        """
        self.is_running = False
        self.target_locked = False
        
        # Lazeri kapat
        self.laser_controller.stop()
        
        # Motorları durdur
        self.motor_controller.stop()
        
        self.logger.info("Mod 1 durduruldu")
    
    def _track_target(self, target: Dict[str, Any]):
        """
        Hedefi takip eder. Motorları hedefin konumuna göre yönlendirir.
        
        Args:
            target: Takip edilecek hedef
        """
        # Hedef koordinatlarını al
        target_x, target_y = target["center"]
        
        # Görüntü merkezinden uzaklık
        dx = target_x - self.frame_center[0]
        dy = target_y - self.frame_center[1]
        
        # Hedefin uzaklığı
        distance = np.sqrt(dx*dx + dy*dy)
        
        # Yüksek güvenilirlik eşiği
        HIGH_CONFIDENCE = 0.6
        
        # Hız faktörünü hesapla (uzaklığa ve güvenilirliğe bağlı)
        speed_factor = min(1.0, distance / 100)  # 100px'den uzaktaysa tam hız
        
        # Güvenilirlik kontrolü (düşük güvenilirlikte daha yavaş hareket)
        if target["confidence"] < HIGH_CONFIDENCE:
            speed_factor *= (target["confidence"] / HIGH_CONFIDENCE)
        
        # Ekran koordinatlarını motor açılarına dönüştür
        # Daha hassas hareketler için geliştirilmiş dönüşüm
        if abs(dx) > 0:
            # Merkeze yaklaştıkça daha hassas hareketler
            scaling_x = 0.05 + 0.05 * (abs(dx) / (self.frame_center[0]))
            horizontal_angle = dx * scaling_x * speed_factor
        else:
            horizontal_angle = 0
            
        if abs(dy) > 0:
            scaling_y = 0.05 + 0.05 * (abs(dy) / (self.frame_center[1]))
            vertical_angle = dy * scaling_y * speed_factor
        else:
            vertical_angle = 0
        
        # Çok küçük açı değişimlerini filtrele (jitter önleme)
        if abs(horizontal_angle) < 0.05:
            horizontal_angle = 0
        if abs(vertical_angle) < 0.05:
            vertical_angle = 0
        
        # Mevcut motor pozisyonlarını al
        current_h, current_v = self.motor_controller.get_current_position()
        
        # Yeni hedef konumunu hesapla
        new_h = current_h + horizontal_angle
        new_v = current_v + vertical_angle
        
        # Eğer hareket gerekiyorsa motorları çalıştır
        if abs(horizontal_angle) > 0 or abs(vertical_angle) > 0:
            # Motor hızını uzaklığa göre ayarla (50-100 arası)
            motor_speed = int(50 + 50 * speed_factor)
            self.motor_controller.move_to_position(new_h, new_v, motor_speed, wait=False)
        
        # Hedef kilitlenme durumunu kontrol et
        # Merkeze daha yakın olmayı gerektir ve yüksek güvenilirlik iste
        is_centered = abs(dx) < 15 and abs(dy) < 15
        high_confidence = target["confidence"] > 0.55
        
        if is_centered and high_confidence:
            if not self.target_locked:
                # Hedef bilgisini oluştur
                target_info = f"{target['class_name']}"
                if 'color' in target:
                    target_info += f" ({target['color']})"
                if 'shape' in target:
                    target_info += f", {target['shape']}"
                
                self.logger.info(f"Hedef kilitlendi: {target_info}")
                self.logger.info(f"  - Pozisyon: {target_x}, {target_y}")
                self.logger.info(f"  - Güvenilirlik: {target['confidence']:.2f}")
                
                self.target_locked = True
                
                # Kilitlenme sesi veya diğer geri bildirim buraya eklenebilir
        else:
            self.target_locked = False
    
    def _fire_at_target(self):
        """
        Hedefe ateş eder.
        """
        if not self.target_locked or not self.current_target:
            self.logger.warning("Hedef kilitli değil, ateş edilemiyor")
            return
        
        # Hedef kilitlenmeden önce son bir pozisyon kontrolü
        target_x, target_y = self.current_target["center"]
        dx = target_x - self.frame_center[0]
        dy = target_y - self.frame_center[1]
        
        if abs(dx) > 15 or abs(dy) > 15:
            self.logger.warning("Hedef merkez dışına çıktı, ateş iptal edildi")
            return
        
        # Lazerin güvenlik kilidini geçici olarak devre dışı bırak
        self.laser_controller.set_safety(False)
        
        try:
            # Lazeri aktifleştir
            self.logger.info(f"Hedefe ateş ediliyor: {self.current_target['class_name']}")
            self.laser_controller.fire(duration=1.5)  # 1.5 saniyelik atış
            
            # Kısa bir bekleme
            time.sleep(0.5)
        finally:
            # Güvenlik kilidini tekrar aktifleştir
            self.laser_controller.set_safety(True)
        
        # Hedefi sıfırla (sonraki hedefi bulmak için)
        self.current_target = None
        self.target_locked = False 