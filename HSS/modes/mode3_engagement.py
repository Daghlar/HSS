"""
Mod 3: Angajman Modu.

Bu modda:
1. Sistem QR kod ve şekil bilgisi ile bir angajman alır:
   - QR kod: Hedef tahtayı belirtir (A veya B)
   - Şekil: Hedef balonun şeklini ve rengini belirtir (örn. kırmızı kare)
2. Kullanıcı angajmanı onaylar
3. Sistem belirtilen tahtaya yönelir ve sadece belirlenen hedefe ateş eder
4. İşlem tamamlandığında sistem durur ve yeni angajman bekler
"""

import time
import logging
import cv2
import numpy as np
from typing import Dict, Any, Tuple, List, Optional

class Mode3:
    """
    Mod 3: Angajman Modu.
    """
    
    def __init__(self, camera, detector, arduino_comm, safety_monitor):
        """
        Mode3 sınıfını başlatır.
        
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
        
        # QR dedektörünü al (ya da oluştur)
        from vision.qr_detector import QRDetector
        self.qr_detector = QRDetector()
        
        # Mod durumu
        self.is_running = False
        self.start_time = 0
        self.timeout = 300  # 5 dakika
        
        # Angajman durumu
        self.state = "SCAN_QR"  # Başlangıç durumu
        self.target_board = None  # Hedef tahta (A veya B)
        self.target_color = None  # Hedef renk
        self.target_shape = None  # Hedef şekil
        
        # Hedef takibi
        self.current_target = None
        self.target_locked = False
        self.lock_time = 0
        self.lock_duration = 1.0  # Kilitli kalma süresi (saniye)
        
        # Görüntü işleme parametreleri
        self.frame_center = (320, 240)  # Varsayılan (640x480 için)
        
        # Angajman istatistikleri
        self.engagement_complete = False
        self.engagement_time = 0
        
        # Logger
        self.logger = logging.getLogger("Mode3")
    
    def run(self, user_input: Dict = None):
        """
        Mod 3'ü çalıştırır.
        
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
        
        # Durum makinesi
        if self.state == "SCAN_QR":
            self._scan_qr_code(frame, user_input)
        elif self.state == "SCAN_SHAPE":
            self._scan_target_shape(frame, user_input)
        elif self.state == "AWAIT_CONFIRMATION":
            self._await_confirmation(frame, user_input)
        elif self.state == "MOVE_TO_BOARD":
            self._move_to_board(frame)
        elif self.state == "SEARCH_TARGET":
            self._search_target(frame)
        elif self.state == "TRACK_TARGET":
            self._track_specific_target(frame)
        elif self.state == "COMPLETED":
            self._engagement_completed(frame)
        else:
            self.logger.error(f"Bilinmeyen durum: {self.state}")
            self.state = "SCAN_QR"
        
        # Zaman aşımı kontrolü
        if self.start_time > 0 and time.time() - self.start_time > self.timeout:
            self.logger.info("Mod 3 zaman aşımı, durduruluyor")
            self._stop()
    
    def _start(self):
        """
        Mod 3'ü başlatır.
        """
        self.is_running = True
        self.start_time = time.time()
        self.state = "SCAN_QR"
        self.target_board = None
        self.target_color = None
        self.target_shape = None
        self.current_target = None
        self.target_locked = False
        self.lock_time = 0
        self.engagement_complete = False
        
        # Kamerayı başlat (eğer başlatılmamışsa)
        if not self.camera.is_working():
            self.camera.initialize()
        
        # YOLO dedektörünü başlat
        self.detector.initialize()
        
        # Motorları kalibre et
        self.motor_controller.calibrate()
        
        self.logger.info("Mod 3 başlatıldı: Angajman Modu")
    
    def _stop(self):
        """
        Mod 3'ü durdurur.
        """
        self.is_running = False
        
        # Lazeri kapat
        self.laser_controller.stop()
        
        # Motorları durdur
        self.motor_controller.stop()
        
        self.logger.info("Mod 3 durduruldu")
    
    def _scan_qr_code(self, frame, user_input):
        """
        QR kodu tarar ve hedef tahtayı belirler.
        
        Args:
            frame: İşlenecek görüntü
            user_input: Kullanıcıdan gelen giriş
        """
        # Hedefleri tespit et
        detections = self.detector.detect(frame)
        
        # QR kod tespiti yap
        qr_success, qr_text = self.qr_detector.find_qr_in_detections(detections, frame)
        
        if qr_success:
            self.logger.info(f"QR kod tespit edildi: {qr_text}")
            
            # QR kod içeriğini doğrula (A veya B olmalı)
            if qr_text == "A" or qr_text == "B":
                self.target_board = qr_text
                self.state = "SCAN_SHAPE"
                self.logger.info(f"Hedef tahta belirlendi: {self.target_board}")
            else:
                self.logger.warning(f"Geçersiz QR kod içeriği: {qr_text}, 'A' veya 'B' bekleniyor")
        
        # Görüntüye tespitleri çiz
        frame_with_detections = self.detector.draw_detections(frame, detections)
    
    def _scan_target_shape(self, frame, user_input):
        """
        Hedef şekli ve rengini tarar.
        
        Args:
            frame: İşlenecek görüntü
            user_input: Kullanıcıdan gelen giriş
        """
        # Hedefleri tespit et
        detections = self.detector.detect(frame)
        
        # Balon renk ve şekil sınıflandırması
        detections = self.detector.classify_balloons(frame, detections)
        detections = self.detector.detect_shapes(frame, detections)
        
        # Balon tespitlerini filtrele
        balloon_detections = [d for d in detections if "balloon" in d["class_name"]]
        
        # Görüntüye tespitleri çiz
        frame_with_detections = self.detector.draw_detections(frame, detections)
        
        # Kullanıcıdan manuel giriş al (tipik olarak GUI'den)
        if user_input and "selected_target" in user_input:
            selected = user_input["selected_target"]
            if "color" in selected and "shape" in selected:
                self.target_color = selected["color"]
                self.target_shape = selected["shape"]
                self.state = "AWAIT_CONFIRMATION"
                self.logger.info(f"Hedef belirlendi: {self.target_color} {self.target_shape}")
        
        # Alternatif olarak, ilk tespit edilen balonun özelliklerini alabilir
        # Bu sadece bir örnek, gerçek senaryoda kullanıcı seçimi daha uygun olur
        elif balloon_detections:
            first_balloon = balloon_detections[0]
            if "color" in first_balloon and "shape" in first_balloon:
                self.target_color = first_balloon["color"]
                self.target_shape = first_balloon["shape"]
                self.state = "AWAIT_CONFIRMATION"
                self.logger.info(f"Hedef belirlendi: {self.target_color} {self.target_shape}")
    
    def _await_confirmation(self, frame, user_input):
        """
        Kullanıcıdan angajman onayı bekler.
        
        Args:
            frame: İşlenecek görüntü
            user_input: Kullanıcıdan gelen giriş
        """
        # Onay için kullanıcıdan giriş bekle
        if user_input:
            if user_input.get("confirm_engagement"):
                self.logger.info("Angajman onaylandı")
                self.state = "MOVE_TO_BOARD"
            elif user_input.get("cancel_engagement"):
                self.logger.info("Angajman iptal edildi")
                self.state = "SCAN_QR"
                self.target_board = None
                self.target_color = None
                self.target_shape = None
    
    def _move_to_board(self, frame):
        """
        Sistemi belirtilen tahtaya yönlendirir.
        
        Args:
            frame: İşlenecek görüntü
        """
        # Tahtaya yönel
        if self.target_board:
            result = self.motor_controller.move_to_board(self.target_board)
            
            if result:
                self.logger.info(f"Tahta {self.target_board}'ya yönelindi")
                self.state = "SEARCH_TARGET"
            else:
                self.logger.error(f"Tahta {self.target_board}'ya yönelinemedi")
                self.state = "SCAN_QR"  # Yeniden başla
                self.target_board = None
    
    def _search_target(self, frame):
        """
        Tahtada belirtilen hedefi arar.
        
        Args:
            frame: İşlenecek görüntü
        """
        # Hedefleri tespit et
        detections = self.detector.detect(frame)
        
        # Balon renk ve şekil sınıflandırması
        detections = self.detector.classify_balloons(frame, detections)
        detections = self.detector.detect_shapes(frame, detections)
        
        # Görüntüye tespitleri çiz
        frame_with_detections = self.detector.draw_detections(frame, detections)
        
        # Hedef kriterlere uyan balonları filtrele
        target_balloons = [
            d for d in detections 
            if "balloon" in d["class_name"] 
            and d.get("color") == self.target_color 
            and d.get("shape") == self.target_shape
        ]
        
        if target_balloons:
            # En yakın hedefi seç
            target = self.detector.find_closest_target(target_balloons, self.frame_center)
            if target:
                self.current_target = target
                self.state = "TRACK_TARGET"
                self.logger.info(f"Hedef bulundu: {self.target_color} {self.target_shape}")
    
    def _track_specific_target(self, frame):
        """
        Belirli bir hedefi takip eder ve ateş eder.
        
        Args:
            frame: İşlenecek görüntü
        """
        if not self.current_target:
            self.state = "SEARCH_TARGET"
            return
        
        # Hedefleri tespit et
        detections = self.detector.detect(frame)
        
        # Balon renk ve şekil sınıflandırması
        detections = self.detector.classify_balloons(frame, detections)
        detections = self.detector.detect_shapes(frame, detections)
        
        # Hedef kriterlere uyan balonları filtrele
        target_balloons = [
            d for d in detections 
            if "balloon" in d["class_name"] 
            and d.get("color") == self.target_color 
            and d.get("shape") == self.target_shape
        ]
        
        # Hedef hala görünür mü?
        if not target_balloons:
            self.logger.warning("Hedef görüş alanından çıktı")
            self.state = "SEARCH_TARGET"
            self.current_target = None
            self.target_locked = False
            self.lock_time = 0
            return
        
        # En yakın hedefi seç
        target = self.detector.find_closest_target(target_balloons, self.frame_center)
        if target:
            self.current_target = target
            
            # Hedefi takip et
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
                    target_info = f"{self.target_color} {self.target_shape}"
                    self.logger.info(f"Hedef kilitlendi: {target_info}")
                    self.target_locked = True
                    self.lock_time = time.time()
                elif time.time() - self.lock_time > self.lock_duration:
                    # Ateş et
                    self._fire_at_specific_target()
            else:
                self.target_locked = False
                self.lock_time = 0
        else:
            self.state = "SEARCH_TARGET"
            self.current_target = None
        
        # Görüntüye tespitleri çiz
        frame_with_detections = self.detector.draw_detections(frame, detections)
    
    def _fire_at_specific_target(self):
        """
        Belirli bir hedefe ateş eder.
        """
        if not self.target_locked or not self.current_target:
            return
        
        # Lazeri aktifleştir
        self.logger.info(f"Hedefe ateş ediliyor: {self.target_color} {self.target_shape}")
        self.laser_controller.fire()
        
        # Kısa bir bekleme
        time.sleep(1)
        
        # Angajmanı tamamla
        self.engagement_complete = True
        self.engagement_time = time.time()
        self.state = "COMPLETED"
    
    def _engagement_completed(self, frame):
        """
        Angajman tamamlandıktan sonraki durum.
        
        Args:
            frame: İşlenecek görüntü
        """
        # Sistemi sıfır pozisyona getir
        self.motor_controller.calibrate()
        
        # Ekrana mesaj çiz
        cv2.putText(frame, "Angajman Tamamlandi", (50, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # İstatistikler
        elapsed_time = time.time() - self.start_time
        cv2.putText(frame, f"Toplam Sure: {elapsed_time:.1f} sn", (50, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        # Yeni angajman için bir süre bekle
        wait_time = 5.0  # saniye
        if time.time() - self.engagement_time > wait_time:
            self.logger.info("Yeni angajman bekleniyor")
            self.state = "SCAN_QR"
            self.target_board = None
            self.target_color = None
            self.target_shape = None
            self.current_target = None
            self.target_locked = False 