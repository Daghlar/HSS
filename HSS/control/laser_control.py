"""
Lazer kontrol modülü.
12V DC güç girişiyle çalışan lazer modülünün kontrolünü sağlar.
MOSFET üzerinden Arduino ile kontrol edilir.
"""

import time
import logging
import threading
from typing import Optional

class LaserController:
    """
    Lazer modülünü kontrol eden sınıf.
    """
    
    def __init__(self, arduino_comm, timeout: float = 2.0):
        """
        LaserController sınıfını başlatır.
        
        Args:
            arduino_comm: Arduino iletişim nesnesi
            timeout: Maksimum lazer açık kalma süresi (saniye)
        """
        self.arduino = arduino_comm
        self.timeout = timeout
        self.is_firing = False
        self.fire_start_time = 0
        self.safety_timer = None
        
        # Logger
        self.logger = logging.getLogger("LaserController")
        
        # Test modu kontrolü
        self.test_mode = not hasattr(arduino_comm, 'serial') or arduino_comm.serial is None
    
    def fire(self, duration: Optional[float] = None) -> bool:
        """
        Lazeri ateşler.
        
        Args:
            duration: Ateşleme süresi (None ise timeout değeri kullanılır)
            
        Returns:
            bool: Ateşleme başarılı ise True
        """
        # Zaten ateşleniyorsa, mevcut ateşlemeyi durdur
        if self.is_firing:
            self.stop()
            
        # Süre belirtilmemişse varsayılan timeout kullan
        if duration is None:
            duration = self.timeout
            
        # Süreyi kontrol et
        if duration <= 0 or duration > self.timeout:
            duration = self.timeout
            
        self.logger.info(f"Lazer ateşleniyor, süre: {duration} saniye")
        
        if self.test_mode:
            # Test modunda
            self.is_firing = True
            self.fire_start_time = time.time()
            
            # Güvenlik için otomatik durdurma
            self.safety_timer = threading.Timer(duration, self.stop)
            self.safety_timer.daemon = True
            self.safety_timer.start()
            
            self.logger.debug(f"Test modu: Lazer ateşlendi, süre: {duration} saniye")
            return True
            
        try:
            # Arduino'ya ateşleme komutu gönder - bu Arduino iletişim formatını kullanır
            result = self.arduino.fire(duration)
            
            if result:
                self.is_firing = True
                self.fire_start_time = time.time()
                
                # Güvenlik için otomatik durdurma
                self.safety_timer = threading.Timer(duration, self.stop)
                self.safety_timer.daemon = True
                self.safety_timer.start()
                
                return True
            else:
                self.logger.error("Ateşleme komutu gönderilemedi")
                return False
                
        except Exception as e:
            self.logger.error(f"Ateşleme hatası: {str(e)}")
            return False
    
    def stop(self) -> bool:
        """
        Lazeri durdurur.
        
        Returns:
            bool: Durdurma başarılı ise True
        """
        if not self.is_firing:
            return True
            
        self.logger.info("Lazer ateşlemesi durduruluyor")
        
        # Güvenlik zamanlayıcısını iptal et
        if self.safety_timer:
            self.safety_timer.cancel()
            self.safety_timer = None
            
        if self.test_mode:
            # Test modunda
            active_duration = time.time() - self.fire_start_time
            self.is_firing = False
            self.logger.debug(f"Test modu: Lazer kapatıldı, çalışma süresi: {active_duration:.2f} saniye")
            return True
            
        try:
            # Arduino'ya durdurma komutu gönder - stop komutu motorları etkilemeden lazeri kapatır
            current_h, current_v = self.arduino.get_servo_position(1), self.arduino.get_servo_position(2)
            result = self.arduino.send_command(f"{current_h},{current_v},0")
            
            if result:
                active_duration = time.time() - self.fire_start_time
                self.is_firing = False
                self.logger.info(f"Lazer kapatıldı, çalışma süresi: {active_duration:.2f} saniye")
                return True
            else:
                self.logger.error("Lazer durdurma komutu gönderilemedi")
                return False
                
        except Exception as e:
            self.logger.error(f"Lazer durdurma hatası: {str(e)}")
            return False
    
    def is_active(self) -> bool:
        """
        Lazerin aktif olup olmadığını kontrol eder.
        
        Returns:
            bool: Lazer aktif ise True
        """
        # Ateşleme durumunu ve aynı zamanda timeout'u kontrol et
        if self.is_firing:
            # Timeout kontrolü
            if time.time() - self.fire_start_time > self.timeout:
                self.stop()  # Zaman aşımı durumunda durdur
                return False
            return True
        return False
    
    def get_active_duration(self) -> float:
        """
        Lazerin aktif olduğu süreyi döndürür.
        
        Returns:
            float: Aktif olduğu süre (saniye)
        """
        if not self.is_firing:
            return 0.0
            
        return time.time() - self.fire_start_time 