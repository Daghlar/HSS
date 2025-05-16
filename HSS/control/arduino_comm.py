"""
Raspberry Pi ve Arduino arasındaki seri iletişimi yöneten modül.
"""

import serial
import json
import time
import threading
import logging
from typing import Dict, Any, Optional, Tuple

class ArduinoComm:
    """
    Arduino ile seri iletişim kuran sınıf.
    JSON formatında mesajlar gönderir ve alır.
    """
    
    def __init__(self, port: str, baudrate: int = 115200):
        """
        ArduinoComm sınıfını başlatır.
        
        Args:
            port: Arduino'nun bağlı olduğu seri port
            baudrate: Seri iletişim hızı
        """
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.running = False
        self.lock = threading.Lock()
        self.last_status = {}
        self.last_temperature = 0.0
        self.emergency_stop_active = False
        
        # Yanıt beklediğimiz komutlar için kuyruk
        self.response_queue = {}
        
        # Logger ayarları
        self.logger = logging.getLogger("ArduinoComm")
        
        self.test_mode = (port == "DUMMY")
        
    def initialize(self) -> bool:
        """
        Arduino ile seri bağlantıyı başlatır.
        
        Returns:
            bool: Bağlantı başarılı ise True, değilse False
        """
        if self.test_mode:
            self.logger.info("Arduino test modunda çalışıyor, gerçek bağlantı yok")
            self.running = True
            self.read_thread = None  # Test modunda okuma thread'i yok
            return True
            
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Arduino'nun resetlenmesi için bekle
            self.running = True
            
            # Arduino'dan veri okuma iş parçacığını başlat
            self.read_thread = threading.Thread(target=self._read_from_arduino)
            self.read_thread.daemon = True
            self.read_thread.start()
            
            self.logger.info(f"Arduino bağlantısı kuruldu: {self.port}")
            return True
            
        except (serial.SerialException, IOError) as e:
            self.logger.error(f"Arduino bağlantısı kurulamadı: {str(e)}")
            return False
    
    def send_command(self, command: Dict[str, Any]) -> bool:
        """
        Arduino'ya JSON formatında komut gönderir.
        
        Args:
            command: Gönderilecek komut (JSON dict formatında)
            
        Returns:
            bool: Gönderim başarılı ise True, değilse False
        """
        if not self.running or not self.serial_conn:
            self.logger.error("Arduino bağlantısı yok. Komut gönderilemiyor.")
            return False
        
        if self.emergency_stop_active and command.get("type") not in ["status", "emergency_reset"]:
            self.logger.warning("Acil durum aktif. Komut engellendi.")
            return False
        
        if self.test_mode:
            self.logger.debug(f"Test modu: Arduino'ya komut gönderildi: {command}")
            return True
        
        try:
            with self.lock:
                # JSON'a çevir ve yeni satır karakteri ekle
                command_str = json.dumps(command) + "\n"
                self.serial_conn.write(command_str.encode())
                self.serial_conn.flush()
                
                # Komut ID'si varsa yanıt bekleme listesine ekle
                if "id" in command:
                    self.response_queue[command["id"]] = None
                
                self.logger.debug(f"Komut gönderildi: {command}")
                return True
                
        except (serial.SerialException, IOError) as e:
            self.logger.error(f"Komut gönderilirken hata oluştu: {str(e)}")
            return False
    
    def _read_from_arduino(self):
        """
        Arduino'dan gelen verileri sürekli okur (arka plan iş parçacığı).
        """
        buffer = ""
        
        while self.running and self.serial_conn:
            try:
                if self.serial_conn.in_waiting > 0:
                    # Mevcut veriyi oku
                    data = self.serial_conn.read(self.serial_conn.in_waiting).decode()
                    buffer += data
                    
                    # Tam JSON mesajı aramak için bufferı kontrol et
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        
                        try:
                            message = json.loads(line)
                            self._process_message(message)
                        except json.JSONDecodeError:
                            self.logger.warning(f"JSON çözümlenirken hata oluştu: {line}")
                
                time.sleep(0.01)  # CPU kullanımını azalt
                
            except (serial.SerialException, IOError) as e:
                self.logger.error(f"Arduino okuma hatası: {str(e)}")
                self.running = False
                break
    
    def _process_message(self, message: Dict[str, Any]):
        """
        Arduino'dan gelen JSON mesajını işler.
        
        Args:
            message: Arduino'dan alınan JSON mesajı
        """
        # Mesaj ID'si varsa, bekleyen yanıtlar listesinde güncelle
        if "id" in message and message["id"] in self.response_queue:
            self.response_queue[message["id"]] = message
        
        # Durum mesajını güncelle
        if message.get("type") == "status":
            self.last_status = message
            
            # Sıcaklık verisi varsa, sakla
            if "temperature" in message:
                self.last_temperature = float(message["temperature"])
            
            # Acil durdurma bilgisi varsa, sakla
            if "emergency_stop" in message:
                self.emergency_stop_active = message["emergency_stop"]
        
        # Hata mesajı geldi mi kontrol et
        if message.get("type") == "error":
            self.logger.error(f"Arduino'dan hata mesajı: {message.get('message', 'Bilinmeyen hata')}")
        
        self.logger.debug(f"Arduino'dan mesaj alındı: {message}")
    
    def wait_for_response(self, command_id: str, timeout: float = 2.0) -> Optional[Dict[str, Any]]:
        """
        Gönderilen bir komutun yanıtını bekler.
        
        Args:
            command_id: Beklenen komut ID'si
            timeout: Zaman aşımı süresi (saniye)
            
        Returns:
            Optional[Dict]: Yanıt gelirse JSON, zaman aşımında None
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if command_id in self.response_queue and self.response_queue[command_id] is not None:
                response = self.response_queue[command_id]
                del self.response_queue[command_id]
                return response
            
            time.sleep(0.01)
        
        # Zaman aşımı
        if command_id in self.response_queue:
            del self.response_queue[command_id]
        
        self.logger.warning(f"Komut yanıtı zaman aşımına uğradı: {command_id}")
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        Arduino'nun son durumunu döndürür.
        
        Returns:
            Dict: Son durum bilgisi
        """
        return self.last_status
    
    def get_temperature(self) -> float:
        """
        Sistemin son sıcaklık değerini döndürür.
        
        Returns:
            float: Sıcaklık (Celsius)
        """
        if self.test_mode:
            return 25.0
        return self.last_temperature
    
    def is_emergency_active(self) -> bool:
        """
        Acil durumun aktif olup olmadığını döndürür.
        
        Returns:
            bool: Acil durum aktif ise True
        """
        return self.emergency_stop_active
    
    def emergency_stop(self):
        """
        Sistemde acil durdurma işlemini başlatır.
        """
        emergency_cmd = {
            "type": "emergency_stop",
            "stop": True
        }
        self.send_command(emergency_cmd)
        self.emergency_stop_active = True
        self.logger.warning("Acil durdurma komutu gönderildi")
    
    def emergency_reset(self):
        """
        Acil durumu sıfırlar.
        """
        reset_cmd = {
            "type": "emergency_reset",
            "reset": True
        }
        self.send_command(reset_cmd)
        self.emergency_stop_active = False
        self.logger.info("Acil durum sıfırlama komutu gönderildi")
    
    def close(self):
        """
        Arduino bağlantısını kapatır.
        """
        self.running = False
        
        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
        
        if self.serial_conn:
            self.serial_conn.close()
            self.serial_conn = None
            
        self.logger.info("Arduino bağlantısı kapatıldı") 