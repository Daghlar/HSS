"""
QR kodları tespit eden ve çözen modül.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Optional, List, Dict, Any

class QRDetector:
    """
    QR kodlarını tespit eden ve çözen sınıf.
    """
    
    def __init__(self):
        """
        QRDetector sınıfını başlatır.
        """
        # OpenCV QR kod okuyucu
        self.qr_detector = cv2.QRCodeDetector()
        
        # Logger
        self.logger = logging.getLogger("QRDetector")
        
    def detect_and_decode(self, frame: np.ndarray) -> Tuple[bool, str, np.ndarray]:
        """
        Görüntüdeki QR kodunu tespit eder ve çözer.
        
        Args:
            frame: İşlenecek görüntü
            
        Returns:
            Tuple[bool, str, np.ndarray]: (başarı, kod metni, QR kod köşeleri)
        """
        if frame is None:
            self.logger.error("Boş görüntü")
            return False, "", np.array([])
            
        try:
            # QR kodu tespit et ve çöz
            decoded_text, points, _ = self.qr_detector.detectAndDecode(frame)
            
            if decoded_text and points is not None:
                self.logger.debug(f"QR kodu tespit edildi: {decoded_text}")
                return True, decoded_text, points
            else:
                return False, "", np.array([])
                
        except Exception as e:
            self.logger.error(f"QR kodu tespit edilirken hata oluştu: {str(e)}")
            return False, "", np.array([])
    
    def find_qr_in_detections(self, detections: List[Dict[str, Any]], frame: np.ndarray) -> Tuple[bool, str]:
        """
        YOLO ile tespit edilen nesneler içinde QR kodlarını arar ve çözer.
        
        Args:
            detections: YOLO ile tespit edilen nesneler listesi
            frame: İşlenecek görüntü
            
        Returns:
            Tuple[bool, str]: (başarı, kod metni)
        """
        # QR kod tespitlerini filtrele
        qr_detections = [d for d in detections if d["class_name"] == "qr_code"]
        
        for detection in qr_detections:
            x, y, w, h = detection["box"]
            
            # Görüntü sınırlarını kontrol et
            if x < 0 or y < 0 or x+w > frame.shape[1] or y+h > frame.shape[0]:
                continue
            
            # QR bölgesini al
            qr_roi = frame[y:y+h, x:x+w]
            
            if qr_roi.size == 0:
                continue
            
            # QR kodunu çöz
            success, text, _ = self.detect_and_decode(qr_roi)
            
            if success:
                detection["qr_text"] = text
                return True, text
        
        return False, ""
    
    def scan_boards_for_qr(self, frame: np.ndarray, board_detections: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Tespit edilen tahtalardaki QR kodlarını tarar.
        
        Args:
            frame: İşlenecek görüntü
            board_detections: Tahta tespitleri
            
        Returns:
            Dict[str, str]: Tahta ID'lerine göre QR kodu metinleri
        """
        result = {}
        
        for detection in board_detections:
            if "board_A" in detection["class_name"] or "board_B" in detection["class_name"]:
                board_id = "A" if "board_A" in detection["class_name"] else "B"
                x, y, w, h = detection["box"]
                
                # Görüntü sınırlarını kontrol et
                if x < 0 or y < 0 or x+w > frame.shape[1] or y+h > frame.shape[0]:
                    continue
                
                # Tahta bölgesini al
                board_roi = frame[y:y+h, x:x+w]
                
                if board_roi.size == 0:
                    continue
                
                # QR kodunu çöz
                success, text, _ = self.detect_and_decode(board_roi)
                
                if success:
                    result[board_id] = text
                    self.logger.info(f"Tahta {board_id} QR kodu: {text}")
        
        return result
    
    def draw_qr_detections(self, frame: np.ndarray, points: np.ndarray, text: str = None) -> np.ndarray:
        """
        QR kod tespitlerini görüntü üzerine çizer.
        
        Args:
            frame: Görüntü
            points: QR kod köşe noktaları
            text: QR kod metni
            
        Returns:
            np.ndarray: Çizimler eklenmiş görüntü
        """
        if points.size == 0:
            return frame
            
        # Çokgeni çiz
        cv2.polylines(frame, [points.astype(np.int32)], True, (0, 255, 0), 2)
        
        # Metin varsa göster
        if text:
            x, y = points[0][0]
            cv2.putText(frame, text, (int(x), int(y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame 