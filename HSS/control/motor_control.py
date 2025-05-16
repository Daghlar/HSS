"""
Step motorların kontrolünü sağlayan modül.
Arduino üzerinden motorlara komut göndermek için ArduinoComm sınıfını kullanır.
"""

import time
import uuid
import logging
from typing import Tuple, Dict, Any, Optional

class MotorController:
    """
    Step motorları kontrol eden sınıf.
    """
    
    def __init__(self, arduino_comm, config=None):
        """
        MotorController sınıfını başlatır.
        
        Args:
            arduino_comm: Arduino ile iletişim için ArduinoComm nesnesi
            config: Yapılandırma parametreleri
        """
        self.arduino = arduino_comm
        
        # Test modu kontrolü
        self.test_mode = arduino_comm.test_mode
        
        # Yapılandırmayı ayarla (config None ise varsayılanları kullan)
        if config is None:
            config = {
                "MOTOR_HORIZONTAL_RANGE": 270,
                "MOTOR_VERTICAL_RANGE": 60,
                "MOTOR_SPEED": 100,
                "RESTRICTED_ZONES": [
                    {"horizontal": (-180, -90), "vertical": (0, 60)},
                    {"horizontal": (90, 180), "vertical": (0, 60)}
                ],
                "BOARD_A_POSITION": -45,
                "BOARD_B_POSITION": 45
            }
            
        self.config = config
        
        # Mevcut pozisyonlar
        self.current_horizontal_position = 0.0  # derece
        self.current_vertical_position = 0.0    # derece
        
        # Hedef pozisyonlar
        self.target_horizontal_position = 0.0   # derece
        self.target_vertical_position = 0.0     # derece
        
        # Hareket durumu
        self.is_moving = False
        
        # Güvenlik kontrolleri
        self.restricted_zones = config.get("RESTRICTED_ZONES", [])
        
        # Logger
        self.logger = logging.getLogger("MotorController")
    
    def move_to_position(self, horizontal: float, vertical: float, speed: int = None, wait: bool = True) -> bool:
        """
        Motorları belirtilen pozisyona hareket ettirir.
        
        Args:
            horizontal: Yatay pozisyon (derece)
            vertical: Dikey pozisyon (derece)
            speed: Motor hızı (0-100)
            wait: Hareket tamamlanana kadar bekle
            
        Returns:
            bool: Hareket başarılı ise True
        """
        # Güvenlik kontrolü
        if not self._is_position_safe(horizontal, vertical):
            self.logger.warning(f"Güvenlik kısıtlaması: {horizontal}, {vertical} konumu yasak bölgede")
            return False
        
        # Sınırları kontrol et
        horizontal = self._clamp_horizontal(horizontal)
        vertical = self._clamp_vertical(vertical)
        
        # Motor hızını ayarla
        if speed is None:
            speed = self.config.get("MOTOR_SPEED", 100)
        
        # Test modunda doğrudan pozisyonları güncelle
        if self.test_mode:
            self.target_horizontal_position = horizontal
            self.target_vertical_position = vertical
            self.current_horizontal_position = horizontal
            self.current_vertical_position = vertical
            self.logger.debug(f"Test modu: Motorlar hareket etti - H:{horizontal}° V:{vertical}°")
            return True
            
        # Komut ID'si oluştur
        command_id = str(uuid.uuid4())
        
        # Arduino'ya komut gönder
        command = {
            "id": command_id,
            "type": "motor",
            "horizontal": horizontal,
            "vertical": vertical,
            "speed": speed
        }
        
        # Hedef pozisyonları güncelle
        self.target_horizontal_position = horizontal
        self.target_vertical_position = vertical
        self.is_moving = True
        
        # Komutu gönder
        if not self.arduino.send_command(command):
            self.is_moving = False
            return False
        
        # Yanıtı bekle
        if wait:
            response = self.arduino.wait_for_response(command_id, timeout=10.0)
            if response and response.get("status") == "success":
                self.current_horizontal_position = horizontal
                self.current_vertical_position = vertical
                self.is_moving = False
                return True
            else:
                self.is_moving = False
                self.logger.error("Motor hareketi başarısız")
                return False
        
        return True
    
    def stop(self) -> bool:
        """
        Motorların hareketini durdurur.
        
        Returns:
            bool: Durdurma başarılı ise True
        """
        # Test modunda
        if self.test_mode:
            self.is_moving = False
            self.logger.debug("Test modu: Motorlar durduruldu")
            return True
            
        command = {
            "type": "motor_stop"
        }
        
        result = self.arduino.send_command(command)
        self.is_moving = False
        return result
    
    def get_current_position(self) -> Tuple[float, float]:
        """
        Mevcut motor pozisyonlarını döndürür.
        
        Returns:
            Tuple[float, float]: (yatay, dikey) derece cinsinden
        """
        return (self.current_horizontal_position, self.current_vertical_position)
    
    def is_in_target_position(self, tolerance: float = 1.0) -> bool:
        """
        Motorların hedef pozisyona ulaşıp ulaşmadığını kontrol eder.
        
        Args:
            tolerance: Pozisyon toleransı (derece)
            
        Returns:
            bool: Hedef pozisyona ulaşıldıysa True
        """
        h_diff = abs(self.current_horizontal_position - self.target_horizontal_position)
        v_diff = abs(self.current_vertical_position - self.target_vertical_position)
        
        return h_diff <= tolerance and v_diff <= tolerance
    
    def calibrate(self) -> bool:
        """
        Motorları kalibre eder (sıfır pozisyona döner).
        
        Returns:
            bool: Kalibrasyon başarılı ise True
        """
        # Test modunda
        if self.test_mode:
            self.current_horizontal_position = 0.0
            self.current_vertical_position = 0.0
            self.target_horizontal_position = 0.0
            self.target_vertical_position = 0.0
            self.is_moving = False
            self.logger.debug("Test modu: Motorlar kalibre edildi")
            return True
            
        command = {
            "type": "calibrate_motors"
        }
        
        result = self.arduino.send_command(command)
        
        if result:
            self.current_horizontal_position = 0.0
            self.current_vertical_position = 0.0
            self.target_horizontal_position = 0.0
            self.target_vertical_position = 0.0
            self.is_moving = False
            self.logger.info("Motorlar kalibre edildi")
        
        return result
    
    def move_relative(self, delta_horizontal: float, delta_vertical: float, speed: int = None) -> bool:
        """
        Mevcut pozisyona göre göreceli hareket yapar.
        
        Args:
            delta_horizontal: Yatay hareket değişimi (derece)
            delta_vertical: Dikey hareket değişimi (derece)
            speed: Motor hızı (0-100)
            
        Returns:
            bool: Hareket başarılı ise True
        """
        new_horizontal = self.current_horizontal_position + delta_horizontal
        new_vertical = self.current_vertical_position + delta_vertical
        
        return self.move_to_position(new_horizontal, new_vertical, speed)
    
    def _clamp_horizontal(self, value: float) -> float:
        """
        Yatay pozisyonu geçerli sınırlar içinde tutar.
        
        Args:
            value: Kontrol edilecek değer
            
        Returns:
            float: Sınırlar içinde tutulan değer
        """
        h_range = self.config.get("MOTOR_HORIZONTAL_RANGE", 270)
        min_h = -h_range / 2
        max_h = h_range / 2
        
        return max(min_h, min(max_h, value))
    
    def _clamp_vertical(self, value: float) -> float:
        """
        Dikey pozisyonu geçerli sınırlar içinde tutar.
        
        Args:
            value: Kontrol edilecek değer
            
        Returns:
            float: Sınırlar içinde tutulan değer
        """
        v_range = self.config.get("MOTOR_VERTICAL_RANGE", 60)
        min_v = 0  # Genellikle 0 derece alt sınır
        max_v = v_range
        
        return max(min_v, min(max_v, value))
    
    def _is_position_safe(self, horizontal: float, vertical: float) -> bool:
        """
        Pozisyonun güvenli olup olmadığını kontrol eder.
        
        Args:
            horizontal: Kontrol edilecek yatay pozisyon
            vertical: Kontrol edilecek dikey pozisyon
            
        Returns:
            bool: Pozisyon güvenli ise True
        """
        # Tüm kısıtlamalı bölgeleri kontrol et
        for zone in self.restricted_zones:
            h_range = zone.get("horizontal", (-180, 180))
            v_range = zone.get("vertical", (0, 60))
            
            if (h_range[0] <= horizontal <= h_range[1] and 
                v_range[0] <= vertical <= v_range[1]):
                return False
        
        return True
    
    def move_to_board(self, board: str) -> bool:
        """
        Belirtilen tahtaya yönelir (A veya B).
        
        Args:
            board: Tahta kimliği ('A' veya 'B')
            
        Returns:
            bool: Hareket başarılı ise True
        """
        if board.upper() == 'A':
            position = self.config.get("BOARD_A_POSITION", -45)
            return self.move_to_position(position, 30)
        elif board.upper() == 'B':
            position = self.config.get("BOARD_B_POSITION", 45)
            return self.move_to_position(position, 30)
        else:
            self.logger.error(f"Geçersiz tahta kimliği: {board}")
            return False
    
    def advanced_calibration(self) -> bool:
        """
        Motorlar için gelişmiş kalibrasyon yapar.
        1. Sınır kontrolleri
        2. Yumuşak hareketlerle sıfır pozisyona dönüş
        3. Ek olarak her eksende doğrulama kontrolü
        
        Returns:
            bool: Kalibrasyon başarılı ise True
        """
        self.logger.info("Gelişmiş motor kalibrasyonu başlatılıyor...")
        
        # Test modunda
        if self.test_mode:
            self.logger.debug("Test modu: Gelişmiş motor kalibrasyonu çalışıyor")
            time.sleep(2.0)  # Simüle edilmiş kalibrasyon süresi
            self.current_horizontal_position = 0.0
            self.current_vertical_position = 0.0
            self.target_horizontal_position = 0.0
            self.target_vertical_position = 0.0
            self.is_moving = False
            self.logger.info("Test modu: Gelişmiş kalibrasyon tamamlandı")
            return True
        
        # Adım 1: Motor sınırlarını kontrol et
        try:
            # Yatay kontrol - Hafifçe sağa dön ve geri dön
            h_check = self.move_to_position(10.0, self.current_vertical_position, 30)
            if not h_check:
                self.logger.error("Yatay motor kontrolü başarısız!")
                return False
            time.sleep(0.5)
            
            # Tekrar merkeze dön
            h_center = self.move_to_position(0.0, self.current_vertical_position, 30)
            if not h_center:
                self.logger.error("Yatay pozisyona dönüş başarısız!")
                return False
            time.sleep(0.5)
            
            # Dikey kontrol - Hafifçe yukarı kalk ve geri dön
            v_check = self.move_to_position(self.current_horizontal_position, 10.0, 30)
            if not v_check:
                self.logger.error("Dikey motor kontrolü başarısız!")
                return False
            time.sleep(0.5)
            
            # Tekrar merkeze dön
            v_center = self.move_to_position(self.current_horizontal_position, 0.0, 30)
            if not v_center:
                self.logger.error("Dikey pozisyona dönüş başarısız!")
                return False
            
            # Adım 2: Tam sıfır pozisyona hassas ayar
            final_cal = self.move_to_position(0.0, 0.0, 20)
            if not final_cal:
                self.logger.error("Son kalibrasyon pozisyonu başarısız!")
                return False
            
            # Başarılı kalibrasyon
            self.current_horizontal_position = 0.0
            self.current_vertical_position = 0.0
            self.target_horizontal_position = 0.0
            self.target_vertical_position = 0.0
            self.is_moving = False
            self.logger.info("Gelişmiş motor kalibrasyonu başarıyla tamamlandı!")
            return True
            
        except Exception as e:
            self.logger.error(f"Kalibrasyon sırasında hata: {str(e)}")
            # Acil durumda en azından sıfır pozisyona dönmeyi dene
            self.move_to_position(0.0, 0.0)
            return False 