"""
YOLOv4 tabanlı nesne tespiti yapan modül.
Balonları, tahtaları ve şekilleri tespit eder.
"""

import cv2
import numpy as np
import logging
import time
import os
from typing import List, Dict, Any, Tuple, Optional

class YoloDetector:
    """
    YOLOv4 tabanlı nesne tespiti yapan sınıf.
    """
    
    def __init__(self, config_path: str, weights_path: str, confidence_threshold: float = 0.5, nms_threshold: float = 0.4):
        """
        YoloDetector sınıfını başlatır.
        
        Args:
            config_path: YOLO config dosya yolu
            weights_path: YOLO ağırlık dosya yolu
            confidence_threshold: Tespit güven eşiği
            nms_threshold: NMS (Non-Maximum Suppression) eşiği
        """
        self.config_path = config_path
        self.weights_path = weights_path
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        
        # Sınıf isimleri
        self.classes = [
            "balloon", "board_A", "board_B", "red_balloon", "blue_balloon",
            "square", "circle", "triangle", "qr_code",
            "person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train",
            "truck", "boat", "helicopter", "drone", "tank"
        ]
        
        # Sınıf renkleri (BGR formatında)
        self.class_colors = {
            "balloon": (0, 165, 255),      # Turuncu
            "board_A": (255, 0, 0),        # Mavi
            "board_B": (0, 0, 255),        # Kırmızı
            "red_balloon": (0, 0, 255),    # Kırmızı
            "blue_balloon": (255, 0, 0),   # Mavi
            "square": (0, 255, 0),         # Yeşil
            "circle": (255, 255, 0),       # Açık mavi
            "triangle": (0, 255, 255),     # Sarı
            "qr_code": (255, 0, 255),      # Mor
            "person": (0, 165, 255),       # Turuncu
            "bicycle": (0, 128, 128),      # Kahverengi
            "car": (128, 0, 128),          # Mor
            "motorbike": (128, 128, 0),    # Deniz mavisi
            "aeroplane": (130, 0, 75),     # Menekşe
            "bus": (0, 69, 255),           # Kırmızı-turuncu
            "train": (100, 110, 240),      # Pembe
            "truck": (204, 50, 153),       # Mor-pembemsi
            "boat": (205, 90, 106),        # Açık mavi
            "helicopter": (0, 128, 255),   # Turuncu
            "drone": (60, 20, 220),        # Kırmızı 
            "tank": (0, 0, 128)            # Koyu kırmızı
        }
        
        # Ağ yapısı
        self.net = None
        self.output_layers = []
        
        # Performans ölçümü
        self.last_inference_time = 0.0
        
        # Tespit istatistikleri
        self.detection_count = 0
        self.total_inference_time = 0.0
        self.inference_count = 0
        
        # Logger
        self.logger = logging.getLogger("YoloDetector")
    
    def initialize(self) -> bool:
        """
        YOLO modelini yükler ve başlatır.
        
        Returns:
            bool: Başlatma başarılı ise True
        """
        try:
            # Modelin var olup olmadığını kontrol et
            if not os.path.exists(self.config_path):
                self.logger.error(f"Config dosyası bulunamadı: {self.config_path}")
                return False
                
            if not os.path.exists(self.weights_path):
                self.logger.error(f"Weights dosyası bulunamadı: {self.weights_path}")
                return False
            
            # YOLO ağını yükle
            self.net = cv2.dnn.readNetFromDarknet(self.config_path, self.weights_path)
            
            # Donanım hızlandırma dene ama güvenli bir şekilde
            has_acceleration = False
            
            # CPU kullanımı (varsayılan)
            self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_DEFAULT)
            self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            
            # Donanım hızlandırma destekleniyorsa etkinleştir
            try:
                # CUDA desteği kontrol etme işlevini çağır
                cv_build_info = cv2.getBuildInformation()
                if "CUDA" in cv_build_info and "YES" in cv_build_info[cv_build_info.find("CUDA"):cv_build_info.find("\n", cv_build_info.find("CUDA"))]:
                    # CUDA destekli
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
                    self.logger.info("CUDA backend etkinleştirildi")
                    has_acceleration = True
            except Exception as e:
                self.logger.warning(f"CUDA etkinleştirilemedi: {str(e)}")
            
            # CUDA çalışmadıysa OpenCL dene
            if not has_acceleration:
                try:
                    # OpenCV desteği
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_OPENCL)
                    self.logger.info("OpenCL backend etkinleştirildi")
                    has_acceleration = True
                except Exception as e:
                    self.logger.warning(f"OpenCL etkinleştirilemedi: {str(e)}")
            
            # Hala hızlandırma yok ise
            if not has_acceleration:
                self.logger.warning("Donanım hızlandırma etkinleştirilemedi, CPU kullanılıyor")
            
            # Çıkış katmanlarını al
            layer_names = self.net.getLayerNames()
            output_layers_indices = self.net.getUnconnectedOutLayers()
            
            # OpenCV versiyonuna bağlı olarak indis tipi değişebilir
            if isinstance(output_layers_indices[0], (list, np.ndarray)):
                self.output_layers = [layer_names[i[0] - 1] for i in output_layers_indices]
            else:
                self.output_layers = [layer_names[i - 1] for i in output_layers_indices]
            
            self.logger.info(f"YOLOv4-tiny modeli başarıyla yüklendi")
            self.logger.info(f"Tespit edilebilir nesneler: {len(self.classes)} sınıf")
            return True
            
        except Exception as e:
            self.logger.error(f"YOLO modeli yüklenirken hata oluştu: {str(e)}")
            return False
    
    def detect(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Verilen görüntüde nesneleri tespit eder.
        
        Args:
            frame: İşlenecek görüntü
            
        Returns:
            List[Dict[str, Any]]: Tespit edilen nesneler listesi
        """
        if self.net is None:
            self.logger.error("YOLO modeli başlatılmamış")
            return []
            
        if frame is None:
            self.logger.error("Boş görüntü")
            return []
        
        # Performans izleme için zaman damgası
        start_time = time.time()
        
        # Görüntü boyutları
        height, width, _ = frame.shape
        
        # Görüntüyü küçült (performans için)
        from config import YOLO_INPUT_SIZE, LOW_PERFORMANCE_MODE
        input_size = YOLO_INPUT_SIZE if 'YOLO_INPUT_SIZE' in globals() else 416
        
        # Düşük performans modunda daha küçük giriş boyutu
        if 'LOW_PERFORMANCE_MODE' in globals() and LOW_PERFORMANCE_MODE:
            input_size = 256
            
        # YOLO için görüntüyü hazırla
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (input_size, input_size), swapRB=True, crop=False)
        
        # İleri yayılım
        self.net.setInput(blob)
        start_time = time.time()
        outputs = self.net.forward(self.output_layers)
        inference_time = time.time() - start_time
        self.last_inference_time = inference_time
        
        # İstatistikleri güncelle
        self.total_inference_time += inference_time
        self.inference_count += 1
        
        # Tespit sonuçlarını işle
        class_ids = []
        confidences = []
        boxes = []
        
        for output in outputs:
            for detection in output:
                scores = detection[5:]
                class_id = np.argmax(scores)
                confidence = scores[class_id]
                
                # Prioritize specified classes for better performance
                class_name = self.classes[class_id] if class_id < len(self.classes) else "unknown"
                
                # Optimize with class filtering
                from config import YOLO_DETECTION_CLASSES
                if 'YOLO_DETECTION_CLASSES' in globals() and YOLO_DETECTION_CLASSES and class_name not in YOLO_DETECTION_CLASSES:
                    if confidence < self.confidence_threshold + 0.1:  # Higher threshold for non-priority classes
                        continue
                
                if confidence > self.confidence_threshold:
                    # Nesne koordinatları
                    center_x = int(detection[0] * width)
                    center_y = int(detection[1] * height)
                    w = int(detection[2] * width)
                    h = int(detection[3] * height)
                    
                    # Çok küçük tespitleri filtrele (muhtemelen yanlış pozitif)
                    min_size = min(width, height) * 0.02  # Görüntünün %2'sinden küçük olanları filtrele
                    if w < min_size or h < min_size:
                        continue
                    
                    # Dikdörtgen koordinatları
                    x = int(center_x - w / 2)
                    y = int(center_y - h / 2)
                    
                    # Listeye ekle
                    boxes.append([x, y, w, h])
                    confidences.append(float(confidence))
                    class_ids.append(class_id)
        
        # Non-maximum suppression ile gereksiz kutuları kaldır
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.nms_threshold)
        
        # Sonuçları biçimlendir
        detections = []
        
        try:
            # Tüm tespitleri işle
            for i in indices:
                # OpenCV versiyonuna bağlı olarak indis tipi değişebilir
                if isinstance(i, (list, np.ndarray)):
                    i = i[0]
                
                box = boxes[i]
                x, y, w, h = box
                
                # Sınırlama kontrolü
                x = max(0, x)
                y = max(0, y)
                
                # Tespit bilgisini oluştur
                class_id = class_ids[i]
                class_name = self.classes[class_id] if class_id < len(self.classes) else "unknown"
                
                detection = {
                    "class_id": class_id,
                    "class_name": class_name,
                    "confidence": confidences[i],
                    "box": (x, y, w, h),
                    "center": (x + w//2, y + h//2)
                }
                
                detections.append(detection)
        except Exception as e:
            self.logger.error(f"Tespit sonuçları işlenirken hata: {str(e)}")
            # Hata durumunda boş liste döndür
            return []
        
        # Tespit sayısını güncelle
        self.detection_count = len(detections)
        self.logger.debug(f"{len(detections)} nesne tespit edildi, çıkarım süresi: {self.last_inference_time:.3f} sn")
        
        return detections
    
    def classify_balloons(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Tespit edilen balonları renk bazında sınıflandırır (kırmızı/mavi).
        
        Args:
            frame: İşlenecek görüntü
            detections: Tespit edilen nesneler listesi
            
        Returns:
            List[Dict[str, Any]]: Renk sınıflandırması eklenmiş tespit listesi
        """
        for i, detection in enumerate(detections):
            if "balloon" in detection["class_name"]:
                # Balon kutusu
                x, y, w, h = detection["box"]
                
                # Görüntü sınırlarını kontrol et
                if x < 0 or y < 0 or x+w > frame.shape[1] or y+h > frame.shape[0]:
                    continue
                
                # Balon bölgesini al
                balloon_roi = frame[y:y+h, x:x+w]
                
                if balloon_roi.size == 0:
                    continue
                
                # HSV'ye dönüştür
                hsv_roi = cv2.cvtColor(balloon_roi, cv2.COLOR_BGR2HSV)
                
                # Ortalama H (Hue) değerini hesapla
                h_channel = hsv_roi[:, :, 0]
                average_h = np.mean(h_channel)
                
                # Renk sınıflandırması
                if 0 <= average_h <= 10 or 170 <= average_h <= 180:
                    detection["color"] = "red"
                    detection["is_enemy"] = True
                elif 100 <= average_h <= 140:
                    detection["color"] = "blue"
                    detection["is_enemy"] = False
                else:
                    detection["color"] = "unknown"
                    detection["is_enemy"] = False
                
        return detections
    
    def detect_shapes(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Tespit edilen balonlardaki şekilleri tanımlar.
        
        Args:
            frame: İşlenecek görüntü
            detections: Tespit edilen nesneler listesi
            
        Returns:
            List[Dict[str, Any]]: Şekil bilgisi eklenmiş tespit listesi
        """
        for detection in detections:
            if "balloon" in detection["class_name"]:
                x, y, w, h = detection["box"]
                
                # Görüntü sınırlarını kontrol et
                if x < 0 or y < 0 or x+w > frame.shape[1] or y+h > frame.shape[0]:
                    continue
                
                # Balon bölgesini al
                balloon_roi = frame[y:y+h, x:x+w]
                
                if balloon_roi.size == 0:
                    continue
                
                # Gri tonlamaya dönüştür ve eşikle
                gray_roi = cv2.cvtColor(balloon_roi, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray_roi, 127, 255, cv2.THRESH_BINARY)
                
                # Konturları bul
                contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                
                if not contours:
                    detection["shape"] = "unknown"
                    continue
                
                # En büyük konturu al
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Kontur yaklaşımı
                epsilon = 0.04 * cv2.arcLength(largest_contour, True)
                approx = cv2.approxPolyDP(largest_contour, epsilon, True)
                
                # Şekil tespiti
                if len(approx) == 3:
                    detection["shape"] = "triangle"
                elif len(approx) == 4:
                    detection["shape"] = "square"
                else:
                    detection["shape"] = "circle"
        
        return detections
    
    def find_closest_target(self, detections: List[Dict[str, Any]], frame_center: Tuple[int, int] = None) -> Optional[Dict[str, Any]]:
        """
        En yakın hedefi bulur.
        
        Args:
            detections: Tespit edilen nesneler listesi
            frame_center: Görüntü merkezi. None ise, görüntü merkezi (0,0) kabul edilir.
            
        Returns:
            Optional[Dict[str, Any]]: En yakın hedef veya hiç yoksa None
        """
        if not detections:
            return None
            
        if frame_center is None:
            frame_center = (0, 0)
            
        # Merkeze olan mesafeyi hesapla
        for detection in detections:
            center_x, center_y = detection["center"]
            dx = center_x - frame_center[0]
            dy = center_y - frame_center[1]
            distance = np.sqrt(dx*dx + dy*dy)
            detection["distance_to_center"] = distance
            
        # Mesafeye göre sırala ve en yakın olanı döndür
        sorted_detections = sorted(detections, key=lambda x: x["distance_to_center"])
        return sorted_detections[0] if sorted_detections else None
    
    def find_closest_enemy(self, detections: List[Dict[str, Any]], frame_center: Tuple[int, int] = None) -> Optional[Dict[str, Any]]:
        """
        En yakın düşman hedefi bulur (sadece kırmızı balonlar).
        
        Args:
            detections: Tespit edilen nesneler listesi
            frame_center: Görüntü merkezi. None ise, görüntü merkezi (0,0) kabul edilir.
            
        Returns:
            Optional[Dict[str, Any]]: En yakın düşman hedef veya hiç yoksa None
        """
        # Sadece düşman hedefleri filtrele
        enemy_detections = [d for d in detections if d.get("is_enemy", False)]
        return self.find_closest_target(enemy_detections, frame_center)
    
    def draw_detections(self, frame: np.ndarray, detections: List[Dict[str, Any]]) -> np.ndarray:
        """
        Tespitleri görüntü üzerine çizer.
        
        Args:
            frame: Görüntü
            detections: Tespit edilen nesneler listesi
            
        Returns:
            np.ndarray: Çizimler eklenmiş görüntü
        """
        frame_out = frame.copy()
        
        for detection in detections:
            x, y, w, h = detection["box"]
            label = detection["class_name"]
            confidence = detection["confidence"]
            
            # Renk bilgisi varsa etikete ekle
            if "color" in detection:
                label = f"{detection['color']} {label}"
            
            # Şekil bilgisi varsa etikete ekle
            if "shape" in detection:
                label = f"{label} ({detection['shape']})"
            
            # Renkleri belirle
            class_name = detection["class_name"]
            border_color = self.class_colors.get(class_name, (255, 255, 255))  # Varsayılan beyaz
            
            # Düşman/dost renk seçimi (balon varsa)
            if "balloon" in class_name:
                if detection.get("is_enemy", False):
                    border_color = (0, 0, 255)  # Kırmızı (BGR)
                else:
                    border_color = (0, 255, 0)  # Yeşil (BGR)
            
            # Merkez noktası
            center_x, center_y = detection["center"]
            
            # Kutuyu çiz (hafif saydam)
            overlay = frame_out.copy()
            cv2.rectangle(overlay, (x, y), (x + w, y + h), border_color, -1)  # Dolgulu
            cv2.addWeighted(overlay, 0.2, frame_out, 0.8, 0, frame_out)  # %20 opaklık
            
            # Kutunun kenarlarını çiz
            cv2.rectangle(frame_out, (x, y), (x + w, y + h), border_color, 2)
            
            # Merkez noktasını çiz
            cv2.circle(frame_out, (center_x, center_y), 3, (0, 255, 255), -1)
            
            # Etiket arka planı
            text_size = cv2.getTextSize(f"{label} {confidence:.2f}", cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame_out, (x, y - 25), (x + text_size[0] + 10, y), border_color, -1)
            
            # Etiketi çiz
            cv2.putText(frame_out, f"{label} {confidence:.2f}", (x + 5, y - 7),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)  # Beyaz metin
        
        # Performans bilgisini ekle
        if self.inference_count > 0:
            avg_inference_time = 1000 * self.total_inference_time / self.inference_count  # ms cinsinden
            cv2.putText(frame_out, f"Inf.Time: {self.last_inference_time*1000:.1f}ms Avg: {avg_inference_time:.1f}ms", 
                       (5, frame_out.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
        
        return frame_out
    
    def get_inference_time(self) -> float:
        """
        Son çıkarım süresini döndürür.
        
        Returns:
            float: Çıkarım süresi (saniye)
        """
        return self.last_inference_time
    
    def get_average_inference_time(self) -> float:
        """
        Ortalama çıkarım süresini döndürür.
        
        Returns:
            float: Ortalama çıkarım süresi (saniye)
        """
        if self.inference_count == 0:
            return 0.0
        return self.total_inference_time / self.inference_count
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """
        Tespit istatistiklerini döndürür.
        
        Returns:
            Dict[str, Any]: Tespit istatistikleri
        """
        return {
            "detection_count": self.detection_count,
            "last_inference_time": self.last_inference_time,
            "average_inference_time": self.get_average_inference_time(),
            "inference_count": self.inference_count
        }
    
    def prioritize_targets(self, detections: List[Dict[str, Any]], frame_center: Tuple[int, int] = None) -> List[Dict[str, Any]]:
        """
        Tespit edilen hedefleri tehdit seviyesine göre önceliklendirir.
        Tehdit seviyesi:
        1. Önce düşman (kırmızı) balonlar
        2. Hedefin boyutu (büyük hedefler daha tehlikeli)
        3. Merkeze olan yakınlık
        4. Güvenilirlik skoru
        
        Args:
            detections: Tespit edilen nesneler listesi
            frame_center: Görüntü merkezi. None ise, (0,0) kabul edilir.
            
        Returns:
            List[Dict[str, Any]]: Önceliklendirilmiş hedef listesi
        """
        if not detections:
            return []
            
        if frame_center is None:
            frame_center = (0, 0)
            
        # Merkeze olan mesafeyi ve tehdit puanını hesapla
        for detection in detections:
            center_x, center_y = detection["center"]
            dx = center_x - frame_center[0]
            dy = center_y - frame_center[1]
            distance = np.sqrt(dx*dx + dy*dy)
            detection["distance_to_center"] = distance
            
            # Boyutu hesapla (daha büyük = daha tehlikeli)
            _, _, w, h = detection["box"]
            size = w * h
            detection["size"] = size
            
            # Tehdit puanı hesapla
            threat_score = 0.0
            
            # 1. Düşman/dost durumu
            if detection.get("is_enemy", False):
                threat_score += 100.0  # Düşman hedefler en yüksek önceliğe sahip
            
            # 2. Hedef türü önem sırası
            if "drone" in detection["class_name"]:
                threat_score += 50.0
            elif "helicopter" in detection["class_name"]:
                threat_score += 40.0
            elif "tank" in detection["class_name"]:
                threat_score += 30.0
            elif "red_balloon" in detection["class_name"]:
                threat_score += 20.0
            elif "balloon" in detection["class_name"]:
                threat_score += 10.0
            
            # 3. Boyut (normalize edilmiş)
            max_size = 640 * 480  # Örnek maksimum boyut
            normalized_size = min(1.0, size / max_size)
            threat_score += normalized_size * 10.0
            
            # 4. Merkeze yakınlık (normalize edilmiş, ters orantılı)
            max_distance = np.sqrt(frame_center[0]**2 + frame_center[1]**2)
            if max_distance > 0:
                normalized_distance = 1.0 - min(1.0, distance / max_distance)
                threat_score += normalized_distance * 15.0
            
            # 5. Güvenilirlik skoru
            threat_score += detection["confidence"] * 10.0
            
            # Toplam tehdit puanını sakla
            detection["threat_score"] = threat_score
            
        # Tehdit puanına göre sırala (yüksekten düşüğe)
        sorted_detections = sorted(detections, key=lambda x: x.get("threat_score", 0), reverse=True)
        
        self.logger.debug(f"Hedefler tehdit seviyesine göre sıralandı: {len(sorted_detections)} hedef")
        if sorted_detections:
            self.logger.debug(f"En yüksek tehdit: {sorted_detections[0].get('class_name')} "
                             f"(Puan: {sorted_detections[0].get('threat_score', 0):.1f})")
        
        return sorted_detections 