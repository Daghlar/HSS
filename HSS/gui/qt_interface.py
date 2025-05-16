"""
Hava Savunma Sistemi (HSS) için PyQt5 tabanlı kullanıcı arayüzü.
"""

import sys
import os
import time
import cv2
import numpy as np
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont, QPalette
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFrame, QGridLayout, QGroupBox,
    QSlider, QSplitter, QTextEdit, QStatusBar
)

from config import *

class VideoThread(QThread):
    """Video akışını yöneten thread sınıfı"""
    frame_update = pyqtSignal(np.ndarray)
    
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.running = False
        
    def run(self):
        self.running = True
        while self.running:
            ret, frame = self.camera.get_frame()
            if ret:
                self.frame_update.emit(frame)
            time.sleep(1/CAMERA_FPS)  # FPS'i sınırla
            
    def stop(self):
        self.running = False
        self.wait()

class SystemStatusWidget(QGroupBox):
    """Sistem durum bilgilerini gösteren widget"""
    
    def __init__(self, parent=None):
        super().__init__("SİSTEM DURUMU", parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QGridLayout()
        self.setLayout(layout)
        
        # Durum göstergeleri için etiketler ve değerler
        self.status_labels = {}
        self.status_values = {}
        
        status_items = [
            {"name": "mode", "label": "Aktif Mod:"},
            {"name": "cpu", "label": "CPU Kullanımı:"},
            {"name": "fps", "label": "Kamera FPS:"},
            {"name": "motor_x", "label": "Motor X:"},
            {"name": "motor_y", "label": "Motor Y:"},
            {"name": "battery", "label": "Batarya:"}
        ]
        
        for i, item in enumerate(status_items):
            row = i // 2
            col = (i % 2) * 2
            
            # Etiket
            label = QLabel(item["label"])
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label, row, col)
            
            # Değer
            value = QLabel("--")
            value.setStyleSheet("color: #3B82F6;")  # Mavi
            layout.addWidget(value, row, col + 1)
            
            # Referansları sakla
            self.status_labels[item["name"]] = label
            self.status_values[item["name"]] = value
    
    def update_status(self, name, value):
        """Durum bilgisini günceller"""
        if name in self.status_values:
            self.status_values[name].setText(str(value))

class CameraViewWidget(QGroupBox):
    """Kamera görüntüsünü gösteren widget"""
    
    def __init__(self, parent=None):
        super().__init__("KAMERA GÖRÜNTÜSÜ & HEDEF TESPİTİ", parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Kamera görüntüsü için etiket
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #1E1E1E; border-radius: 5px;")
        layout.addWidget(self.image_label)
        
        # FPS göstergesi
        self.fps_label = QLabel("FPS: --")
        self.fps_label.setStyleSheet("color: #3B82F6; font-weight: bold;")
        self.fps_label.setAlignment(Qt.AlignRight)
        layout.addWidget(self.fps_label)
        
    def update_frame(self, frame):
        """Kamera karesini günceller"""
        height, width, channel = frame.shape
        bytes_per_line = 3 * width
        q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        self.image_label.setPixmap(QPixmap.fromImage(q_image).scaled(
            self.image_label.width(), self.image_label.height(), 
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

class ControlPanelWidget(QGroupBox):
    """Kontrol paneli widget'ı"""
    
    def __init__(self, parent=None):
        super().__init__("KONTROL PANELİ", parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Mod seçimi
        mode_group = QGroupBox("Çalışma Modu")
        mode_layout = QVBoxLayout()
        mode_group.setLayout(mode_layout)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["MANUEL MOD", "OTONOM MOD"])
        self.mode_combo.setStyleSheet("font-weight: bold; height: 30px;")
        mode_layout.addWidget(self.mode_combo)
        
        layout.addWidget(mode_group)
        
        # Kontrol butonları
        control_group = QGroupBox("Kontrol Komutları")
        control_layout = QGridLayout()
        control_group.setLayout(control_layout)
        
        # Ateş et butonu
        self.fire_button = QPushButton("ATEŞ ET")
        self.fire_button.setStyleSheet(
            "background-color: #EF4444; color: white; font-weight: bold; height: 40px;"
        )
        control_layout.addWidget(self.fire_button, 0, 0)
        
        # Kalibrasyon butonu
        self.calibrate_button = QPushButton("KALİBRE ET")
        self.calibrate_button.setStyleSheet(
            "background-color: #3B82F6; color: white; font-weight: bold; height: 40px;"
        )
        control_layout.addWidget(self.calibrate_button, 0, 1)
        
        # Acil durdurma butonu
        self.emergency_button = QPushButton("ACİL DURDURMA")
        self.emergency_button.setStyleSheet(
            "background-color: #B91C1C; color: white; font-weight: bold; height: 50px;"
        )
        control_layout.addWidget(self.emergency_button, 1, 0, 1, 2)
        
        layout.addWidget(control_group)
        
        # Bağlantı durumu
        conn_group = QGroupBox("Bağlantı Durumu")
        conn_layout = QVBoxLayout()
        conn_group.setLayout(conn_layout)
        
        self.camera_status = QLabel("◉ KAMERA: BAĞLI")
        self.camera_status.setStyleSheet("color: #10B981;")  # Yeşil
        conn_layout.addWidget(self.camera_status)
        
        self.arduino_status = QLabel("◉ ARDUINO: BAĞLI")
        self.arduino_status.setStyleSheet("color: #10B981;")  # Yeşil
        conn_layout.addWidget(self.arduino_status)
        
        self.system_status = QLabel("◉ SİSTEM: AKTİF")
        self.system_status.setStyleSheet("color: #10B981; font-weight: bold;")  # Yeşil
        conn_layout.addWidget(self.system_status)
        
        layout.addWidget(conn_group)
        
        # Log gösterimi
        log_group = QGroupBox("Sistem Logları")
        log_layout = QVBoxLayout()
        log_group.setLayout(log_layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background-color: #1E1E1E; color: #E0E0E0;")
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
        
    def add_log(self, message, level="INFO"):
        """Log mesajı ekler"""
        timestamp = time.strftime("%H:%M:%S")
        color = {
            "INFO": "#3B82F6",    # Mavi
            "WARNING": "#F59E0B",  # Sarı
            "ERROR": "#EF4444",    # Kırmızı
            "SUCCESS": "#10B981"   # Yeşil
        }.get(level, "#E0E0E0")
        
        self.log_text.append(f'<span style="color:{color}">[{timestamp}] [{level}]</span> {message}')
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

class TargetInfoWidget(QGroupBox):
    """Hedef bilgilerini gösteren widget"""
    
    def __init__(self, parent=None):
        super().__init__("HEDEF BİLGİLERİ", parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QGridLayout()
        self.setLayout(layout)
        
        # Hedef bilgileri için etiketler ve değerler
        self.target_labels = {}
        self.target_values = {}
        
        target_items = [
            {"name": "konum_x", "label": "Hedef X:"},
            {"name": "konum_y", "label": "Hedef Y:"},
            {"name": "uzaklik", "label": "Uzaklık:"},
            {"name": "genislik", "label": "Genişlik:"},
            {"name": "yukseklik", "label": "Yükseklik:"},
            {"name": "guven", "label": "Güven:"}
        ]
        
        for i, item in enumerate(target_items):
            row = i // 3
            col = (i % 3) * 2
            
            # Etiket
            label = QLabel(item["label"])
            label.setStyleSheet("font-weight: bold;")
            layout.addWidget(label, row, col)
            
            # Değer
            value = QLabel("--")
            value.setStyleSheet("color: #3B82F6;")  # Mavi
            layout.addWidget(value, row, col + 1)
            
            # Referansları sakla
            self.target_labels[item["name"]] = label
            self.target_values[item["name"]] = value
    
    def update_target(self, name, value):
        """Hedef bilgisini günceller"""
        if name in self.target_values:
            self.target_values[name].setText(str(value))

class HSSMainWindow(QMainWindow):
    """Ana pencere sınıfı"""
    
    def __init__(self, system):
        super().__init__()
        self.system = system
        self.last_frame_time = time.time()
        self.frame_count = 0
        self.fps = 0
        
        self.init_ui()
        self.setup_connections()
        
    def init_ui(self):
        """Kullanıcı arayüzünü başlatır"""
        self.setWindowTitle("HSS - HAVA SAVUNMA SİSTEMİ KONTROL MERKEZİ")
        self.setGeometry(100, 100, 1280, 800)
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #111827;
                color: #F1F5F9;
                font-family: 'Roboto', sans-serif;
            }
            QGroupBox {
                border: 1px solid #374151;
                border-radius: 8px;
                margin-top: 1ex;
                font-weight: bold;
                font-size: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #3B82F6;
            }
        """)
        
        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Ana düzen - yatay bölünmüş
        main_layout = QHBoxLayout(central_widget)
        
        # Sol panel - kontrol paneli
        self.control_panel = ControlPanelWidget()
        control_panel_container = QWidget()
        control_panel_layout = QVBoxLayout(control_panel_container)
        control_panel_layout.addWidget(self.control_panel)
        
        # Sağ panel - kamera ve durum bilgileri
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Kamera görünümü
        self.camera_view = CameraViewWidget()
        right_layout.addWidget(self.camera_view, 3)
        
        # Alt panel - hedef ve durum bilgileri
        bottom_panel = QWidget()
        bottom_layout = QHBoxLayout(bottom_panel)
        
        # Hedef bilgileri
        self.target_info = TargetInfoWidget()
        bottom_layout.addWidget(self.target_info)
        
        # Sistem durum bilgileri
        self.system_status = SystemStatusWidget()
        bottom_layout.addWidget(self.system_status)
        
        right_layout.addWidget(bottom_panel, 1)
        
        # Ana düzene panelleri ekle
        main_layout.addWidget(control_panel_container, 1)
        main_layout.addWidget(right_panel, 3)
        
        # Durum çubuğu
        self.statusBar().showMessage("Sistem hazır")
        
        # Timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_ui)
        self.update_timer.start(UI_UPDATE_RATE)
        
    def setup_connections(self):
        """Sinyal ve yuva bağlantılarını kurar"""
        # Video thread'ini başlat
        self.video_thread = VideoThread(self.system.camera)
        self.video_thread.frame_update.connect(self.process_frame)
        self.video_thread.start()
        
        # Buton bağlantıları
        self.control_panel.fire_button.clicked.connect(self.on_fire_button)
        self.control_panel.calibrate_button.clicked.connect(self.on_calibrate_button)
        self.control_panel.emergency_button.clicked.connect(self.on_emergency_button)
        self.control_panel.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        
        # Başlangıç log mesajı
        self.control_panel.add_log("HSS sistemi başlatıldı", "SUCCESS")
    
    def process_frame(self, frame):
        """Kameradan gelen kareyi işler"""
        # Kare sayacını artır
        self.frame_count += 1
        
        # FPS hesapla
        current_time = time.time()
        if current_time - self.last_frame_time >= 1.0:
            self.fps = self.frame_count
            self.frame_count = 0
            self.last_frame_time = current_time
            self.camera_view.fps_label.setText(f"FPS: {self.fps}")
            
        # YOLO tespiti (her N karede bir)
        self.yolo_frame_count = getattr(self, 'yolo_frame_count', 0) + 1
        if self.yolo_frame_count % YOLO_PROCESS_EVERY_N_FRAME == 0:
            # Görüntü işleme ve tespit
            detections = self.system.detector.detect(frame)
            
            # Tespit sonuçlarını çiz
            if detections:
                for detection in detections:
                    # Sınırlayıcı kutu
                    x, y, w, h = detection["box"]
                    label = detection.get("class", "Nesne")
                    confidence = detection.get("confidence", 0)
                    
                    # Kutu rengi
                    color = (255, 0, 0) if label == "mavi_balon" else (0, 0, 255)
                    
                    # Çerçeve çiz
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                    
                    # Etiket metni
                    text = f"{label}: {confidence:.2f}"
                    
                    # Etiket
                    cv2.putText(frame, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.5, (255, 255, 255), 1)
                    
                # İlk hedefin bilgilerini göster
                detection = detections[0]
                x, y, w, h = detection["box"]
                self.target_info.update_target("konum_x", f"{x + w//2} px")
                self.target_info.update_target("konum_y", f"{y + h//2} px")
                self.target_info.update_target("genislik", f"{w} px")
                self.target_info.update_target("yukseklik", f"{h} px")
                self.target_info.update_target("guven", f"{detection.get('confidence', 0):.2f}")
                self.target_info.update_target("uzaklik", "1.5 m")  # Örnek değer
            
        # Kareyi görüntüle
        self.camera_view.update_frame(frame)
    
    def update_ui(self):
        """UI bileşenlerini günceller"""
        # Sistem durum bilgilerini güncelle
        self.system_status.update_status("mode", "MANUEL MOD" if self.control_panel.mode_combo.currentIndex() == 0 else "OTONOM MOD")
        
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=None)
            self.system_status.update_status("cpu", f"{cpu_percent:.1f}%")
        except (ImportError, Exception):
            pass
        
        self.system_status.update_status("fps", f"{self.fps}")
        
        # Motor pozisyonlarını güncelle
        if hasattr(self.system, 'arduino') and self.system.arduino.is_connected():
            motor_x = self.system.arduino.get_servo_position(1)
            motor_y = self.system.arduino.get_servo_position(2)
            self.system_status.update_status("motor_x", f"{motor_x}°")
            self.system_status.update_status("motor_y", f"{motor_y}°")
            
            # Batarya durumu (örnek)
            self.system_status.update_status("battery", "92%")
    
    def on_fire_button(self):
        """Ateş butonu işlevi"""
        self.control_panel.add_log("Ateş komutu gönderildi", "WARNING")
        self.system.user_input["fire"] = True
    
    def on_calibrate_button(self):
        """Kalibrasyon butonu işlevi"""
        self.control_panel.add_log("Motor kalibrasyonu başlatıldı", "INFO")
        if hasattr(self.system, 'safety') and hasattr(self.system.safety, 'motor_controller'):
            result = self.system.safety.motor_controller.calibrate()
            if result:
                self.control_panel.add_log("Kalibrasyon başarıyla tamamlandı", "SUCCESS")
            else:
                self.control_panel.add_log("Kalibrasyon başarısız oldu", "ERROR")
    
    def on_emergency_button(self):
        """Acil durdurma butonu işlevi"""
        self.control_panel.add_log("ACİL DURDURMA butonu basıldı!", "ERROR")
        if hasattr(self.system, 'arduino'):
            self.system.arduino.emergency_stop()
    
    def on_mode_changed(self, index):
        """Mod değişikliği işlevi"""
        mode_name = "MANUEL MOD" if index == 0 else "OTONOM MOD"
        self.control_panel.add_log(f"Çalışma modu değiştirildi: {mode_name}", "INFO")
        self.system.current_mode = index + 1  # Mod 1: Manuel, Mod 2: Otonom
    
    def closeEvent(self, event):
        """Pencere kapatılma olayı"""
        # Video thread'ini durdur
        if hasattr(self, 'video_thread'):
            self.video_thread.stop()
        # Timer'ı durdur
        self.update_timer.stop()
        # Sistemi durdur
        self.system.stop()
        event.accept()


def run_qt_interface(system):
    """PyQt5 arayüzünü başlatır"""
    app = QApplication(sys.argv)
    
    # Tema ve font ayarları
    app.setStyle("Fusion")
    
    # Koyu tema
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(28, 28, 28))
    palette.setColor(QPalette.WindowText, QColor(230, 230, 230))
    palette.setColor(QPalette.Base, QColor(15, 15, 15))
    palette.setColor(QPalette.AlternateBase, QColor(35, 35, 35))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(230, 230, 230))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, QColor(230, 230, 230))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(59, 130, 246))
    palette.setColor(QPalette.Highlight, QColor(59, 130, 246))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    app.setPalette(palette)
    
    window = HSSMainWindow(system)
    window.show()
    
    return app.exec_() 