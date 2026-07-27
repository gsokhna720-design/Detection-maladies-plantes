// ============================================================
//  PlantAI — ESP32-CAM : capture + envoi image WiFi UNIQUEMENT
//  Serveur HTTP : /capture, :81/stream, /status
//  Compatible avec le backend PlantAI FastAPI (/api/esp32/*)
//
//  Ce module ne gère ni capteurs (DHT11/humidité sol — voir esp32_devkit.ino)
//  ni servomoteur (voir arduino_uno.ino). Responsabilité unique : la caméra.
//
//  INSTALLATION :
//  1. Arduino IDE → Outils → Carte → "AI Thinker ESP32-CAM"
//  2. Espressif boards manager URL :
//     https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
//  3. Copier secrets.h.example en secrets.h et y renseigner WIFI_SSID / WIFI_PASS
//  4. Flasher → Ouvrir le moniteur série 115200 → noter l'IP
//  5. Entrer cette IP dans PlantAI → badge ESP32-CAM
// ============================================================

#include "esp_camera.h"
#include "esp_http_server.h"
#include <WiFi.h>

// ── Configuration WiFi ──────────────────────────────────────
// SSID / mot de passe définis dans secrets.h (non commité — voir secrets.h.example)
#include "secrets.h"

// ── Pins caméra AI Thinker ESP32-CAM ───────────────────────
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define LED_PIN            4  // Flash LED

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CT =
  "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART =
  "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t camera_httpd = NULL;
httpd_handle_t stream_httpd = NULL;

// ════════════════════════════════════════════════════════════
bool initCamera() {
  camera_config_t cfg;
  cfg.ledc_channel = LEDC_CHANNEL_0;
  cfg.ledc_timer   = LEDC_TIMER_0;
  cfg.pin_d0 = Y2_GPIO_NUM; cfg.pin_d1 = Y3_GPIO_NUM;
  cfg.pin_d2 = Y4_GPIO_NUM; cfg.pin_d3 = Y5_GPIO_NUM;
  cfg.pin_d4 = Y6_GPIO_NUM; cfg.pin_d5 = Y7_GPIO_NUM;
  cfg.pin_d6 = Y8_GPIO_NUM; cfg.pin_d7 = Y9_GPIO_NUM;
  cfg.pin_xclk     = XCLK_GPIO_NUM;
  cfg.pin_pclk     = PCLK_GPIO_NUM;
  cfg.pin_vsync    = VSYNC_GPIO_NUM;
  cfg.pin_href     = HREF_GPIO_NUM;
  cfg.pin_sscb_sda = SIOD_GPIO_NUM;
  cfg.pin_sscb_scl = SIOC_GPIO_NUM;
  cfg.pin_pwdn     = PWDN_GPIO_NUM;
  cfg.pin_reset    = RESET_GPIO_NUM;
  cfg.xclk_freq_hz = 20000000;
  cfg.pixel_format = PIXFORMAT_JPEG;
  cfg.frame_size   = FRAMESIZE_VGA;  // 640x480 — stable et suffisant pour l'IA
  cfg.jpeg_quality = 10;
  cfg.fb_count     = 1;
  Serial.println("Resolution : VGA 640x480");
  if (esp_camera_init(&cfg) != ESP_OK) return false;
  // Auto-balance / exposition
  sensor_t* s = esp_camera_sensor_get();
  s->set_whitebal(s, 1);
  s->set_awb_gain(s, 1);
  s->set_exposure_ctrl(s, 1);
  s->set_gain_ctrl(s, 1);
  s->set_raw_gma(s, 1);
  s->set_lenc(s, 1);
  return true;
}

// ── GET / ────────────────────────────────────────────────────
static esp_err_t index_handler(httpd_req_t* req) {
  char html[1024];
  String ip = WiFi.localIP().toString();
  snprintf(html, sizeof(html),
    "<!DOCTYPE html><html><head><meta charset='UTF-8'>"
    "<title>PlantAI ESP32-CAM</title>"
    "<style>body{font-family:Arial;background:#0f1117;color:#f1f5f9;padding:24px}"
    "h1{color:#1db954}pre{background:#1a1d27;padding:14px;border-radius:10px;color:#4ade80}</style>"
    "</head><body>"
    "<h1>PlantAI ESP32-CAM</h1>"
    "<p>Camera operationnelle sur <strong>%s</strong></p>"
    "<img src='http://%s:81/stream' style='max-width:640px;border-radius:10px;border:2px solid #1db954'/>"
    "<pre>"
    "Capture : http://%s/capture\n"
    "Stream  : http://%s:81/stream\n"
    "Statut  : http://%s/status\n"
    "</pre>"
    "<p>Entrez <strong>%s</strong> dans PlantAI pour connecter la camera.</p>"
    "</body></html>",
    ip.c_str(), ip.c_str(),
    ip.c_str(), ip.c_str(), ip.c_str(),
    ip.c_str());
  httpd_resp_set_type(req, "text/html");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, html, strlen(html));
}

// ── GET /capture ─────────────────────────────────────────────
static esp_err_t capture_handler(httpd_req_t* req) {
  digitalWrite(LED_PIN, HIGH);
  camera_fb_t* fb = esp_camera_fb_get();
  digitalWrite(LED_PIN, LOW);
  if (!fb) { httpd_resp_send_500(req); return ESP_FAIL; }
  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  esp_err_t res = httpd_resp_send(req, (const char*)fb->buf, fb->len);
  Serial.printf("Capture OK : %u octets\n", fb->len);
  esp_camera_fb_return(fb);
  return res;
}

// ── GET /status ──────────────────────────────────────────────
static esp_err_t status_handler(httpd_req_t* req) {
  String ip = WiFi.localIP().toString();
  String json = "{\"status\":\"ok\",\"ip\":\"" + ip + "\""
                ",\"rssi\":" + String(WiFi.RSSI()) +
                ",\"stream_url\":\"http://" + ip + ":81/stream\""
                ",\"capture_url\":\"http://" + ip + "/capture\"}";
  httpd_resp_set_type(req, "application/json");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  return httpd_resp_send(req, json.c_str(), json.length());
}

// ── GET :81/stream ────────────────────────────────────────────
static esp_err_t stream_handler(httpd_req_t* req) {
  char part_buf[64];
  httpd_resp_set_type(req, STREAM_CT);
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  while (true) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) break;
    size_t hlen = snprintf(part_buf, 64, STREAM_PART, fb->len);
    esp_err_t res = httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, part_buf, hlen);
    if (res == ESP_OK) res = httpd_resp_send_chunk(req, (const char*)fb->buf, fb->len);
    esp_camera_fb_return(fb);
    if (res != ESP_OK) break;
  }
  return ESP_OK;
}

void startServers() {
  httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
  cfg.server_port = 80;
  httpd_uri_t uris[] = {
    { "/",        HTTP_GET, index_handler,   NULL },
    { "/capture", HTTP_GET, capture_handler, NULL },
    { "/status",  HTTP_GET, status_handler,  NULL },
  };
  if (httpd_start(&camera_httpd, &cfg) == ESP_OK)
    for (auto& u : uris) httpd_register_uri_handler(camera_httpd, &u);

  httpd_config_t scfg = HTTPD_DEFAULT_CONFIG();
  scfg.server_port = 81;
  scfg.ctrl_port   = 32769;
  httpd_uri_t stream_uri = { "/stream", HTTP_GET, stream_handler, NULL };
  if (httpd_start(&stream_httpd, &scfg) == ESP_OK)
    httpd_register_uri_handler(stream_httpd, &stream_uri);
}

// ════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  Serial.println("\n=== PlantAI ESP32-CAM ===");
  if (!initCamera()) {
    Serial.println("ERREUR camera ! Redemarrage...");
    delay(3000); ESP.restart();
  }
  Serial.println("Camera OK");

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
  String ip = WiFi.localIP().toString();
  Serial.println("\n========================");
  Serial.println("  PLANTAI ESP32-CAM PRET");
  Serial.println("========================");
  Serial.print  ("  IP       : "); Serial.println(ip);
  Serial.print  ("  Capture  : http://"); Serial.print(ip); Serial.println("/capture");
  Serial.print  ("  Stream   : http://"); Serial.print(ip); Serial.println(":81/stream");
  Serial.println("  Entrez cette IP dans PlantAI !");
  Serial.println("========================\n");

  startServers();

  // 3 flashs = pret
  for (int i=0; i<3; i++) {
    digitalWrite(LED_PIN, HIGH); delay(150);
    digitalWrite(LED_PIN, LOW);  delay(150);
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi perdu, reconnexion...");
    WiFi.reconnect();
    delay(5000);
    if (WiFi.status() != WL_CONNECTED) ESP.restart();
  }
  delay(5000);
}
