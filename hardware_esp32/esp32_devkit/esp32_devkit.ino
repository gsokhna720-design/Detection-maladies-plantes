// ============================================================
//  PlantAI — ESP32 DevKit : capteurs environnementaux UNIQUEMENT
//  DHT11 (température + humidité air) + capteur d'humidité du sol
//  Envoi périodique en WiFi (HTTP POST) vers le backend PlantAI FastAPI
//
//  Carte différente de l'ESP32-CAM (esp32cam.ino) : ce module n'a pas
//  de caméra, c'est un ESP32 DevKit "générique" dédié aux capteurs IoT.
//
//  Branchement :
//    DHT11 DATA        → GPIO 13   (VCC → 3.3V, GND → GND)
//    Capteur humidité sol (sortie analogique) → GPIO 34 (ADC1_CH6)
//
//  INSTALLATION :
//  1. Arduino IDE → Outils → Carte → "ESP32 Dev Module"
//  2. Copier secrets.h.example en secrets.h et y renseigner WIFI_SSID / WIFI_PASS
//     + BACKEND_URL (ex: "http://192.168.1.50:5000")
//  3. Installer les libs "DHT sensor library" (Adafruit) + "Adafruit Unified Sensor"
//  4. Flasher → le module envoie une mesure toutes les SEND_INTERVAL_MS
// ============================================================

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

// ── Configuration WiFi + URL backend ────────────────────────
// SSID / mot de passe / BACKEND_URL définis dans secrets.h (non commité)
#include "secrets.h"

// ── Capteur DHT11 — température + humidité ambiante ────────
#define DHT_PIN  13
#define DHT_TYPE DHT11
DHT dht(DHT_PIN, DHT_TYPE);

// ── Capteur d'humidité du sol (sonde capacitive, sortie analogique) ─
#define SOIL_PIN 34
// Étalonnage : valeur ADC brute en sol sec / sol saturé d'eau (à ajuster
// selon la sonde utilisée — mesurer avec le moniteur série).
#define SOIL_DRY  3000
#define SOIL_WET  1200

const unsigned long SEND_INTERVAL_MS = 60000;  // 1 mesure / minute
unsigned long lastSend = 0;

// ════════════════════════════════════════════════════════════
float readSoilHumidityPercent() {
  int raw = analogRead(SOIL_PIN);
  float pct = map(raw, SOIL_DRY, SOIL_WET, 0, 100);
  if (pct < 0)   pct = 0;
  if (pct > 100) pct = 100;
  return pct;
}

void sendSensorData(float tempAir, float humAir, float humSol) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  String url = String(BACKEND_URL) + "/sensors/data";
  http.begin(url);
  http.addHeader("Content-Type", "application/json");

  char payload[160];
  snprintf(payload, sizeof(payload),
    "{\"temperatureAir\":%.1f,\"humiditeAir\":%.1f,\"humiditeSol\":%.1f}",
    tempAir, humAir, humSol);

  int code = http.POST(payload);
  Serial.printf("POST /sensors/data → HTTP %d\n", code);
  http.end();
}

// ════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  Serial.println("\n=== PlantAI ESP32 DevKit — Capteurs ===");

  dht.begin();
  Serial.println("DHT11 initialise (GPIO 13)");
  Serial.println("Capteur humidite sol initialise (GPIO 34)");

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  int t = 0;
  while (WiFi.status() != WL_CONNECTED && t++ < 40) {
    delay(500); Serial.print(".");
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nECHEC WiFi. Redemarrage...");
    delay(3000); ESP.restart();
  }
  Serial.println("\nWiFi connecte : " + WiFi.localIP().toString());
  Serial.println("Backend cible : " + String(BACKEND_URL));
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi perdu, reconnexion...");
    WiFi.reconnect();
    delay(5000);
    return;
  }

  if (millis() - lastSend >= SEND_INTERVAL_MS) {
    lastSend = millis();

    float t = dht.readTemperature();
    float h = dht.readHumidity();
    float soil = readSoilHumidityPercent();

    if (isnan(t) || isnan(h)) {
      Serial.println("Erreur lecture DHT11");
      return;
    }

    Serial.printf("Temp=%.1fC  HumAir=%.1f%%  HumSol=%.1f%%\n", t, h, soil);
    sendSensorData(t, h, soil);
  }
}
