"""
Sistem güvenlik izleme modülü.
Sıcaklık, acil durdurma ve diğer güvenlik özelliklerini kontrol eder.
"""

import time
import logging
import threading
from typing import Dict, Any

from control.motor_control import MotorController
from control.laser_control import LaserController

class SafetyMonitor:
    """
    Sistem güvenliğini izleyen sınıf.
    """
    
    def __init__(self, arduino_comm):
        """
        SafetyMonitor sınıfını başlatır.
        
        Args:
            arduino_comm: Arduino iletişim nesnesi
        """
        self.arduino = arduino_comm
        self.test_mode = arduino_comm.test_mode
        
        # Motor ve lazer kontrol nesneleri
        self.motor_controller = MotorController(arduino_comm)
        self.laser_controller = LaserController(arduino_comm)
        
        # Güvenlik parametreleri
        self.max_temperature = 75.0  # Maksimum güvenli sıcaklık (°C)
        self.is_system_safe_flag = True
        
        # İzleme iş parçacığı
        self.monitoring_thread = None
        self.running = False
        
        # İzleme aralığı (saniye)
        self.monitoring_interval = 1.0
        
        # Son durum bilgisi
        self.status = {
            "temperature": 0.0,
            "motor_h_pos": 0,
            "motor_v_pos": 0,
            "laser_active": False,
            "fan_active": False,
            "emergency_stop": False,
            "status": "Normal"
        }
        
        # İş parçacığı kilidi
        self.lock = threading.Lock()
        
        # Logger
        self.logger = logging.getLogger("SafetyMonitor")
    
    def start_monitoring(self):
        """
        Güvenlik izleme iş parçacığını başlatır.
        """
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
            
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        self.logger.info("Güvenlik izleme başlatıldı")
    
    def _monitoring_loop(self):
        """
        Sistem güvenliğini sürekli izleyen döngü (arka plan iş parçacığı).
        """
        while self.running:
            try:
                # Test modunda örnek veriler gönder
                if self.test_mode:
                    with self.lock:
                        self.status = {
                            "temperature": 25.0 + 5.0 * (time.time() % 10) / 10.0,  # 25-30 arası dalgalanma
                            "motor_h_pos": int(45 * (time.time() % 20) / 20.0 - 22.5),  # -22.5 ile 22.5 arası
                            "motor_v_pos": int(30 * (time.time() % 10) / 10.0 - 15),   # -15 ile 15 arası
                            "laser_active": False,
                            "fan_active": False,
                            "emergency_stop": False,
                            "status": "Normal"
                        }
                        self.is_system_safe_flag = True
                    time.sleep(self.monitoring_interval)
                    continue
                
                # Arduino'dan durum bilgisini al
                arduino_status = self.arduino.read_status()
                
                if arduino_status:
                    with self.lock:
                        # Durum bilgisini güncelle
                        self.status.update(arduino_status)
                        
                        # Güvenlik kontrolü
                        self._check_safety()
                
                # İzleme aralığı kadar bekle
                time.sleep(self.monitoring_interval)
                    
            except Exception as e:
                self.logger.error(f"Güvenlik izleme hatası: {str(e)}")
                time.sleep(self.monitoring_interval)
    
    def _check_safety(self):
        """
        Güvenlik kontrollerini yapar ve gerektiğinde güvenlik önlemleri alır.
        """
        # Sıcaklık kontrolü
        temperature = self.status.get("temperature", 0.0)
        
        if temperature > self.max_temperature:
            self.logger.warning(f"Sıcaklık kritik seviyede: {temperature}°C")
            self.is_system_safe_flag = False
            self.status["status"] = "Yüksek Sıcaklık"
            
            # Lazeri kapat
            self.laser_controller.stop()
            
            # Soğutma fanlarını çalıştır
            self.arduino.send_command({"type": "fan", "state": True})
            
        # Acil durum butonu kontrolü
        emergency_stop = self.status.get("emergency_stop", False)
        
        if emergency_stop:
            self.logger.warning("Acil durdurma butonu aktif")
            self.is_system_safe_flag = False
            self.status["status"] = "Acil Durdurma"
            
            # Tüm sistemleri durdur
            self.laser_controller.stop()
            self.motor_controller.stop()
            
        # Herşey normalde
        if not emergency_stop and temperature <= self.max_temperature:
            self.is_system_safe_flag = True
            self.status["status"] = "Normal"
    
    def is_system_safe(self) -> bool:
        """
        Sistemin güvenli durumda olup olmadığını döndürür.
        
        Returns:
            bool: Sistem güvenliyse True
        """
        if self.test_mode:
            return True
            
        with self.lock:
            return self.is_system_safe_flag
    
    def get_status(self) -> Dict[str, Any]:
        """
        Mevcut durum bilgisini döndürür.
        
        Returns:
            Dict[str, Any]: Durum bilgisi
        """
        with self.lock:
            return self.status.copy()
    
    def shutdown(self):
        """
        Güvenlik izlemeyi durdurur ve kaynakları serbest bırakır.
        """
        self.running = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=2.0)
            
        # Güvenlik önlemi olarak lazeri kapat
        self.laser_controller.stop()
        
        self.logger.info("Güvenlik izleme durduruldu") 