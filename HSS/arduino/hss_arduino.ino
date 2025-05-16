/**
 * Hava Savunma Sistemi (HSS) Arduino Kontrolcüsü
 * 
 * Bu kod, Raspberry Pi ile Arduino arasındaki iletişimi sağlar.
 * Step motorları, lazeri ve fanları kontrol eder.
 * Sıcaklık sensöründen veri okur.
 * Acil durdurma butonunu izler.
 */

#include <ArduinoJson.h>
#include <Stepper.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// Pin tanımlamaları
const int STEP_MOTOR_H_PIN1 = 2;
const int STEP_MOTOR_H_PIN2 = 3;
const int STEP_MOTOR_H_PIN3 = 4;
const int STEP_MOTOR_H_PIN4 = 5;

const int STEP_MOTOR_V_PIN1 = 6;
const int STEP_MOTOR_V_PIN2 = 7;
const int STEP_MOTOR_V_PIN3 = 8;
const int STEP_MOTOR_V_PIN4 = 9;

const int LASER_PIN = 10;
const int FAN_PIN = 11;
const int TEMP_SENSOR_PIN = 12;
const int EMERGENCY_STOP_PIN = 13;

// Stepper motor ayarları
const int STEPS_PER_REVOLUTION = 200;  // Adım başına devir sayısı
Stepper stepperH(STEPS_PER_REVOLUTION, STEP_MOTOR_H_PIN1, STEP_MOTOR_H_PIN2, STEP_MOTOR_H_PIN3, STEP_MOTOR_H_PIN4);
Stepper stepperV(STEPS_PER_REVOLUTION, STEP_MOTOR_V_PIN1, STEP_MOTOR_V_PIN2, STEP_MOTOR_V_PIN3, STEP_MOTOR_V_PIN4);

// Sıcaklık sensörü ayarları
OneWire oneWire(TEMP_SENSOR_PIN);
DallasTemperature sensors(&oneWire);

// Sistem durumu
float currentTemperature = 0.0;
bool emergencyStop = false;
bool laserActive = false;
bool fanActive = false;

// Motor pozisyonları (derece)
float currentHorizontalPos = 0.0;
float currentVerticalPos = 0.0;
float targetHorizontalPos = 0.0;
float targetVerticalPos = 0.0;

// Lazer zaman aşımı
unsigned long laserActivationTime = 0;
unsigned long laserTimeout = 2000;  // milisaniye

void setup() {
  // Seri port başlat
  Serial.begin(115200);
  
  // Pinleri ayarla
  pinMode(LASER_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);
  pinMode(EMERGENCY_STOP_PIN, INPUT_PULLUP);
  
  // Motor hızını ayarla
  stepperH.setSpeed(60);  // RPM
  stepperV.setSpeed(60);  // RPM
  
  // Sıcaklık sensörünü başlat
  sensors.begin();
  
  // Başlangıç durumları
  digitalWrite(LASER_PIN, LOW);
  digitalWrite(FAN_PIN, LOW);
  
  // Hoşgeldin mesajı
  sendStatusMessage("Arduino başlatıldı");
}

void loop() {
  // Seri porttan komut oku
  readCommands();
  
  // Acil durdurma butonunu kontrol et
  checkEmergencyStop();
  
  // Motorları kontrol et
  controlMotors();
  
  // Lazeri kontrol et
  controlLaser();
  
  // Sıcaklığı oku ve durumu gönder (her 1 saniyede bir)
  static unsigned long lastStatusTime = 0;
  if (millis() - lastStatusTime > 1000) {
    readTemperature();
    sendStatusUpdate();
    lastStatusTime = millis();
  }
}

void readCommands() {
  if (Serial.available()) {
    // JSON verisini oku
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, Serial);
    
    if (error) {
      sendErrorMessage("JSON çözümleme hatası");
      return;
    }
    
    // Komut tipini al
    const char* commandType = doc["type"];
    
    // Komut ID'si varsa sakla (yanıt için)
    String commandId = "";
    if (doc.containsKey("id")) {
      commandId = doc["id"].as<String>();
    }
    
    // Komut tipine göre işlem yap
    if (strcmp(commandType, "motor") == 0) {
      handleMotorCommand(doc, commandId);
    }
    else if (strcmp(commandType, "laser") == 0) {
      handleLaserCommand(doc, commandId);
    }
    else if (strcmp(commandType, "fan") == 0) {
      handleFanCommand(doc, commandId);
    }
    else if (strcmp(commandType, "status") == 0) {
      sendStatusUpdate();
    }
    else if (strcmp(commandType, "emergency_stop") == 0) {
      emergencyStop = doc["stop"];
      sendCommandResponse(commandId, true, "Acil durdurma uygulandı");
    }
    else if (strcmp(commandType, "emergency_reset") == 0) {
      emergencyStop = false;
      sendCommandResponse(commandId, true, "Acil durum sıfırlandı");
    }
    else if (strcmp(commandType, "calibrate_motors") == 0) {
      calibrateMotors(commandId);
    }
    else {
      sendErrorMessage("Bilinmeyen komut tipi");
    }
  }
}

void handleMotorCommand(const JsonDocument& doc, String commandId) {
  if (emergencyStop) {
    sendCommandResponse(commandId, false, "Acil durum aktif, motorlar kilitli");
    return;
  }
  
  if (doc.containsKey("horizontal")) {
    targetHorizontalPos = doc["horizontal"];
  }
  
  if (doc.containsKey("vertical")) {
    targetVerticalPos = doc["vertical"];
  }
  
  int speed = 60;
  if (doc.containsKey("speed")) {
    speed = doc["speed"];
    stepperH.setSpeed(speed);
    stepperV.setSpeed(speed);
  }
  
  sendCommandResponse(commandId, true, "Motor komutu alındı");
}

void handleLaserCommand(const JsonDocument& doc, String commandId) {
  if (emergencyStop) {
    sendCommandResponse(commandId, false, "Acil durum aktif, lazer devre dışı");
    return;
  }
  
  bool state = doc["state"];
  
  if (state) {
    // Lazeri aktifleştir
    digitalWrite(LASER_PIN, HIGH);
    laserActive = true;
    laserActivationTime = millis();
    
    // Zaman aşımını ayarla (varsa)
    if (doc.containsKey("duration")) {
      float duration = doc["duration"];
      laserTimeout = (unsigned long)(duration * 1000);
    }
    
    sendCommandResponse(commandId, true, "Lazer aktifleştirildi");
  }
  else {
    // Lazeri deaktifleştir
    digitalWrite(LASER_PIN, LOW);
    laserActive = false;
    sendCommandResponse(commandId, true, "Lazer deaktifleştirildi");
  }
}

void handleFanCommand(const JsonDocument& doc, String commandId) {
  bool state = doc["state"];
  
  if (state) {
    // Fanları aktifleştir
    digitalWrite(FAN_PIN, HIGH);
    fanActive = true;
    sendCommandResponse(commandId, true, "Fanlar aktifleştirildi");
  }
  else {
    // Fanları deaktifleştir
    digitalWrite(FAN_PIN, LOW);
    fanActive = false;
    sendCommandResponse(commandId, true, "Fanlar deaktifleştirildi");
  }
}

void calibrateMotors(String commandId) {
  if (emergencyStop) {
    sendCommandResponse(commandId, false, "Acil durum aktif, kalibrasyon yapılamıyor");
    return;
  }
  
  // Motorları sıfır konumuna getir
  targetHorizontalPos = 0.0;
  targetVerticalPos = 0.0;
  
  sendCommandResponse(commandId, true, "Motorlar kalibre edildi");
}

void checkEmergencyStop() {
  // Acil durdurma butonu basıldı mı kontrol et
  bool buttonPressed = (digitalRead(EMERGENCY_STOP_PIN) == LOW);
  
  if (buttonPressed && !emergencyStop) {
    // Acil durum tetiklendi
    emergencyStop = true;
    
    // Lazeri kapat
    digitalWrite(LASER_PIN, LOW);
    laserActive = false;
    
    // Motorları durdur
    stopMotors();
    
    sendStatusMessage("Acil durum butonu basıldı");
  }
}

void stopMotors() {
  // Motorları mevcut konumlarında durdur
  targetHorizontalPos = currentHorizontalPos;
  targetVerticalPos = currentVerticalPos;
}

void controlMotors() {
  if (emergencyStop) {
    return;
  }
  
  // Yatay motor kontrolü
  if (targetHorizontalPos != currentHorizontalPos) {
    // Farkı hesapla
    float diffH = targetHorizontalPos - currentHorizontalPos;
    
    // Adım atılacak mı kontrol et
    if (abs(diffH) > 0.1) {
      int steps = (diffH > 0) ? 1 : -1;
      stepperH.step(steps);
      
      // Pozisyonu güncelle (her adım yaklaşık 1.8 derece)
      currentHorizontalPos += steps * (360.0 / STEPS_PER_REVOLUTION);
    }
  }
  
  // Dikey motor kontrolü
  if (targetVerticalPos != currentVerticalPos) {
    // Farkı hesapla
    float diffV = targetVerticalPos - currentVerticalPos;
    
    // Adım atılacak mı kontrol et
    if (abs(diffV) > 0.1) {
      int steps = (diffV > 0) ? 1 : -1;
      stepperV.step(steps);
      
      // Pozisyonu güncelle (her adım yaklaşık 1.8 derece)
      currentVerticalPos += steps * (360.0 / STEPS_PER_REVOLUTION);
    }
  }
}

void controlLaser() {
  // Lazer aktifse zaman aşımını kontrol et
  if (laserActive) {
    unsigned long currentTime = millis();
    
    if (currentTime - laserActivationTime > laserTimeout) {
      // Zaman aşımı, lazeri kapat
      digitalWrite(LASER_PIN, LOW);
      laserActive = false;
      sendStatusMessage("Lazer zaman aşımı, deaktifleştirildi");
    }
  }
}

void readTemperature() {
  // Sıcaklık sensöründen veri oku
  sensors.requestTemperatures();
  currentTemperature = sensors.getTempCByIndex(0);
  
  // Geçersiz değer kontrolü
  if (currentTemperature < -50 || currentTemperature > 100) {
    currentTemperature = 25.0;  // Varsayılan değer
  }
}

void sendStatusUpdate() {
  StaticJsonDocument<256> doc;
  
  doc["type"] = "status";
  doc["temperature"] = currentTemperature;
  doc["horizontal_pos"] = currentHorizontalPos;
  doc["vertical_pos"] = currentVerticalPos;
  doc["laser_active"] = laserActive;
  doc["fan_active"] = fanActive;
  doc["emergency_stop"] = emergencyStop;
  
  serializeJson(doc, Serial);
  Serial.println();
}

void sendCommandResponse(String commandId, bool success, const char* message) {
  if (commandId.length() == 0) {
    return;
  }
  
  StaticJsonDocument<256> doc;
  
  doc["id"] = commandId;
  doc["status"] = success ? "success" : "error";
  doc["message"] = message;
  
  serializeJson(doc, Serial);
  Serial.println();
}

void sendErrorMessage(const char* message) {
  StaticJsonDocument<256> doc;
  
  doc["type"] = "error";
  doc["message"] = message;
  
  serializeJson(doc, Serial);
  Serial.println();
}

void sendStatusMessage(const char* message) {
  StaticJsonDocument<256> doc;
  
  doc["type"] = "status_message";
  doc["message"] = message;
  
  serializeJson(doc, Serial);
  Serial.println();
} 