"""
Kamera görüntüsünü yakalayan ve yöneten modül.
"""

import cv2
import time
import logging
import threading
import numpy as np
from typing import Tuple, Optional

class Camera:
    """
    Kamera yönetimi ve görüntü yakalama sınıfı.
    """
    
    def __init__(self, camera_id: int, width: int = 640, height: int = 480, fps: int = 30):
        """
        Camera sınıfını başlatır.
        
        Args:
            camera_id: Kamera ID
            width: Görüntü genişliği
            height: Görüntü yüksekliği
            fps: Saniyedeki kare sayısı
        """
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        
        self.camera = None
        self.running = False
        
        # Test modu (-1 ID ise test modu aktif)
        self.test_mode = (camera_id == -1)
        
        # Son kare ve zaman damgası
        self.last_frame = None
        self.last_timestamp = 0.0
        
        # İş parçacığı kilidi
        self.lock = threading.Lock()
        
        # Logger
        self.logger = logging.getLogger("Camera")
    
    def initialize(self) -> bool:
        """
        Kamera bağlantısını başlatır.
        
        Returns:
            bool: Başlatma başarılı ise True
        """
        # Test modu kontrolü
        if self.test_mode:
            self.logger.info("Kamera test modunda başlatıldı")
            self.running = True
            
            # Test görüntüsü oluştur
            self.last_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            cv2.putText(self.last_frame, "TEST MODU", (50, self.height//2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            self.last_timestamp = time.time()
            
            # Test modu için ayrı bir thread başlat
            self.capture_thread = threading.Thread(target=self._test_mode_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            return True
            
        try:
            self.camera = cv2.VideoCapture(self.camera_id)
            
            # Özellikleri ayarla
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Kameranın hazır olup olmadığını kontrol et
            if not self.camera.isOpened():
                self.logger.error(f"Kamera başlatılamadı: {self.camera_id}")
                return False
            
            # Kare yakalama iş parçacığını başlat
            self.running = True
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            self.logger.info(f"Kamera başlatıldı: {self.camera_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Kamera başlatılırken hata oluştu: {str(e)}")
            return False
    
    def _test_mode_loop(self):
        """
        Test modu için sahte görüntü oluşturan döngü.
        """
        while self.running:
            try:
                with self.lock:
                    # Hareketli test görüntüsü oluştur
                    self.last_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
                    
                    # Zaman damgası (saat:dakika:saniye)
                    time_str = time.strftime("%H:%M:%S")
                    cv2.putText(self.last_frame, f"TEST MODU - {time_str}", 
                               (50, self.height//2), cv2.FONT_HERSHEY_SIMPLEX, 
                               1, (0, 255, 0), 2)
                    
                    # Hareketli daire çiz
                    t = time.time()
                    x = int(self.width/2 + 100 * np.cos(t))
                    y = int(self.height/2 + 100 * np.sin(t))
                    cv2.circle(self.last_frame, (x, y), 20, (0, 0, 255), -1)
                    
                    self.last_timestamp = time.time()
                    
                time.sleep(0.033)  # ~30 FPS
                    
            except Exception as e:
                self.logger.error(f"Test modu hatası: {str(e)}")
                time.sleep(0.1)
    
    def _capture_loop(self):
        """
        Sürekli olarak kameradan görüntü yakalar (arka plan iş parçacığı).
        """
        while self.running and self.camera:
            try:
                ret, frame = self.camera.read()
                
                if ret and frame is not None:
                    with self.lock:
                        self.last_frame = frame.copy()
                        self.last_timestamp = time.time()
                else:
                    self.logger.warning("Kameradan kare yakalanamadı")
                    time.sleep(0.1)  # Hata durumunda çok fazla CPU kullanmamak için bekle
                    
            except Exception as e:
                self.logger.error(f"Kare yakalama hatası: {str(e)}")
                time.sleep(0.1)
    
    def get_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """
        Son yakalanan kareyi döndürür.
        
        Returns:
            Tuple[bool, Optional[np.ndarray]]: (başarı, kare)
        """
        with self.lock:
            if self.last_frame is None:
                return False, None
                
            frame = self.last_frame.copy()
            current_time = time.time()
            
            # Kareler çok eski ise uyarı ver (test modunda kontrolü atla)
            if not self.test_mode and current_time - self.last_timestamp > 1.0:  # 1 saniyeden eski
                self.logger.warning("Eski kare kullanılıyor")
                
            return True, frame
    
    def is_working(self) -> bool:
        """
        Kameranın çalışıp çalışmadığını kontrol eder.
        
        Returns:
            bool: Kamera çalışıyorsa True
        """
        # Test modunda her zaman çalışıyor olarak kabul et
        if self.test_mode:
            return True
            
        # Kameranın çalışıp çalışmadığını ve son karenin güncel olup olmadığını kontrol et
        if not self.running or not self.camera or not self.camera.isOpened():
            return False
            
        current_time = time.time()
        with self.lock:
            # Son 3 saniye içinde kare almadıysak, kamera çalışmıyor sayılır
            if current_time - self.last_timestamp > 3.0:
                return False
                
        return True
    
    def release(self):
        """
        Kamera kaynağını serbest bırakır.
        """
        self.running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
            
        if self.camera and not self.test_mode:
            self.camera.release()
            self.camera = None
            
        self.logger.info("Kamera kapatıldı")
        
    def __del__(self):
        """
        Destructor metodu, kaynakları serbest bırakır.
        """
        self.release() 