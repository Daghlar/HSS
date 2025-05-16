"""
Mod 2: Otomatik Takip, Otomatik Ates (Dost-Düşman Ayrımı).

Bu modda:
1. Balonlar renk bazında sınıflandırılır (kırmızı = düşman, mavi = dost)
2. Sadece düşman balonlar (kırmızı) takip edilir
3. Hedef kilitlendiğinde sistem otomatik olarak ateş eder
4. Dost balonlara (mavi) ateş edilmez
"""

import time
import logging
import cv2
import numpy as np
from typing import Dict, Any, Tuple, List

class Mode2:
    """
    Mod 2: Otomatik Takip, Otomatik Ates modu.
    """
    
    def __init__(self, camera, detector, arduino_comm, safety_monitor):
        """
        Mode2 sınıfını başlatır.
        
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
        self.lock_time = 0  # Kilitlenme zamanı
        self.lock_duration = 1.0  # Kilitli kalma süresi (saniye)
        
        # Görüntü işleme parametreleri
        self.frame_center = (320, 240)  # Varsayılan (640x480 için)
        
        # Takip parametreleri
        self.is_cooldown = False
        self.cooldown_time = 0
        self.cooldown_duration = 2.0  # Ateş sonrası bekleme süresi (saniye)
        
        # Logger
        self.logger = logging.getLogger("Mode2")
    
    def run(self):
        """
        Mod 2'yi çalıştırır.
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
        
        # Düşman hedefleri (kırmızı balonlar) filtrele
        enemy_detections = [d for d in detections if d.get("is_enemy", False)]
        
        # Bekleme süresi kontrolü
        if self.is_cooldown:
            if time.time() - self.cooldown_time > self.cooldown_duration:
                self.is_cooldown = False
            else:
                # Bekleme süresi dolmadıysa çalışmaya devam et
                # ama ateş etme ve hedef kilitleme yapma
                pass
        
        # Düşman hedef varsa ve bekleme modunda değilsek takip et
        if enemy_detections and not self.is_cooldown:
            # Hedefleri tehdit seviyesine göre önceliklendir
            prioritized_targets = self.detector.prioritize_targets(enemy_detections, self.frame_center)
            
            if prioritized_targets:
                # En yüksek öncelikli hedefi seç
                highest_priority_target = prioritized_targets[0]
                
                # Hedefin tehdit seviyesini logla
                threat_score = highest_priority_target.get("threat_score", 0)
                self.logger.debug(f"En yüksek öncelikli hedef: {highest_priority_target['class_name']} "
                                 f"(Tehdit: {threat_score:.1f})")
                
                self.current_target = highest_priority_target
                self._track_target(highest_priority_target)
                
                # Hedef kilitliyse ve yeterince süre kilitli kaldıysa ateş et
                if self.target_locked:
                    if self.lock_time == 0:
                        self.lock_time = time.time()
                    elif time.time() - self.lock_time > self.lock_duration:
                        self._fire_at_target()
            else:
                self.current_target = None
                self.target_locked = False
                self.lock_time = 0
        else:
            self.current_target = None
            self.target_locked = False
            self.lock_time = 0
        
        # Görüntüye tespitleri çiz
        frame_with_detections = self.detector.draw_detections(frame, detections)
        
        # Zaman aşımı kontrolü
        if self.start_time > 0 and time.time() - self.start_time > self.timeout:
            self.logger.info("Mod 2 zaman aşımı, durduruluyor")
            self._stop()
    
    def _start(self):
        """
        Mod 2'yi başlatır.
        """
        self.is_running = True
        self.start_time = time.time()
        self.target_locked = False
        self.lock_time = 0
        self.is_cooldown = False
        
        # Kamerayı başlat (eğer başlatılmamışsa)
        if not self.camera.is_working():
            self.camera.initialize()
        
        # YOLO dedektörünü başlat
        self.detector.initialize()
        
        # Motorları kalibre et
        self.motor_controller.calibrate()
        
        self.logger.info("Mod 2 başlatıldı: Otomatik Takip, Otomatik Ates")
    
    def _stop(self):
        """
        Mod 2'yi durdurur.
        """
        self.is_running = False
        self.target_locked = False
        
        # Lazeri kapat
        self.laser_controller.stop()
        
        # Motorları durdur
        self.motor_controller.stop()
        
        self.logger.info("Mod 2 durduruldu")
    
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
        
        # Ekran koordinatlarını motor açılarına dönüştür
        horizontal_angle = dx * 0.1  # Yatay açı (derece)
        vertical_angle = dy * 0.1    # Dikey açı (derece)
        
        # Mevcut motor pozisyonlarını al
        current_h, current_v = self.motor_controller.get_current_position()
        
        # Yeni hedef konumunu hesapla
        new_h = current_h + horizontal_angle
        new_v = current_v + vertical_angle
        
        # Motorları yeni konuma getir
        self.motor_controller.move_to_position(new_h, new_v)
        
        # Hedef kilitlenme durumunu kontrol et
        is_centered = abs(dx) < 20 and abs(dy) < 20
        
        if is_centered:
            if not self.target_locked:
                target_info = f"{target['class_name']}"
                if 'color' in target:
                    target_info += f" ({target['color']})"
                if 'shape' in target:
                    target_info += f", {target['shape']}"
                
                self.logger.info(f"Düşman hedef kilitlendi: {target_info}")
                self.target_locked = True
        else:
            self.target_locked = False
            self.lock_time = 0
    
    def _fire_at_target(self):
        """
        Hedefe ateş eder.
        """
        if not self.target_locked or not self.current_target:
            return
        
        # Düşman olduğundan emin ol
        if not self.current_target.get("is_enemy", False):
            self.logger.warning("Dost hedef, ateş edilmiyor")
            return
        
        # Lazeri aktifleştir
        self.logger.info(f"Düşman hedefe ateş ediliyor: {self.current_target['class_name']}")
        self.laser_controller.fire()
        
        # Bekleme modunu aktifleştir
        self.is_cooldown = True
        self.cooldown_time = time.time()
        
        # Hedefi sıfırla
        self.current_target = None
        self.target_locked = False
        self.lock_time = 0 