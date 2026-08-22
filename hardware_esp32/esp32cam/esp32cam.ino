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

// ── Reglages capture (perf + stabilite) ─────────────────────────────────────
// Le CNN cote backend redimensionne TOUJOURS l'image en 224x224 (ia/model.py,
// IMG_SIZE = 224). Capturer en VGA 640x480 ne sert donc a rien pour l'IA : les
// pixels supplementaires sont jetes juste avant la prediction, mais ils coutent
// ~4x plus de temps de capture et ~4x plus d'octets a transferer en WiFi —
// c'est-a-dire ~4x plus de fenetre pendant laquelle le transfert peut etre
// coupe. QVGA 320x240 reste tres au-dessus des 224x224 utiles.
// Si l'image affichee parait trop petite dans l'interface, remonter a
// FRAMESIZE_HVGA (480x320) ou FRAMESIZE_VGA (640x480) : c'est la seule ligne
// a changer.
#define CAPTURE_FRAMESIZE  FRAMESIZE_QVGA   // 320x240

// 10 = meilleure qualite / gros fichier, 63 = pire qualite / petit fichier.
// 12 divise a peu pres par deux le poids du JPEG pour une perte invisible
// apres le redimensionnement en 224x224.
#define CAPTURE_JPEG_QUALITY 12

// Nombre d'images jetees avant la bonne : le capteur OV2640 sort des trames
// sombres/vertes tant que l'auto-exposition (AEC) et l'auto-gain (AGC) ne se
// sont pas stabilises. C'est la cause classique d'une photo noire alors que le
// flux :81/stream, lui, est correct (il enchaine les trames, donc il se
// stabilise tout seul).
#define WARMUP_FRAMES 2

// Flash LED (GPIO4) DESACTIVE par defaut. A pleine puissance il tire un pic de
// courant que la plupart des alimentations USB/FTDI utilisees avec l'ESP32-CAM
// ne suivent pas : la tension chute, la radio WiFi decroche ou le module
// redemarre — exactement le symptome "connexion perdue par intermittence
// quelques secondes apres une connexion confirmee". L'eclairage d'une salle
// suffit largement. Mettre a 1 uniquement si la scene est vraiment sombre ET
// que la carte est alimentee par une source 5V >= 1A (pas le port USB d'un
// programmateur FTDI).
#define USE_FLASH 0

#define PART_BOUNDARY "123456789000000000000987654321"
static const char* STREAM_CT =
  "multipart/x-mixed-replace;boundary=" PART_BOUNDARY;
static const char* STREAM_BOUNDARY = "\r\n--" PART_BOUNDARY "\r\n";
static const char* STREAM_PART =
  "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t camera_httpd = NULL;
httpd_handle_t stream_httpd = NULL;

// ════════════════════════════════════════════════════════════
// Libelle lisible pour le moniteur serie (evite d'afficher une resolution
// codee en dur qui ne correspond plus a CAPTURE_FRAMESIZE).
static const char* framesizeLabel(framesize_t fs) {
  switch (fs) {
    case FRAMESIZE_QQVGA: return "QQVGA 160x120";
    case FRAMESIZE_QVGA:  return "QVGA 320x240";
    case FRAMESIZE_CIF:   return "CIF 400x296";
    case FRAMESIZE_HVGA:  return "HVGA 480x320";
    case FRAMESIZE_VGA:   return "VGA 640x480";
    case FRAMESIZE_SVGA:  return "SVGA 800x600";
    case FRAMESIZE_XGA:   return "XGA 1024x768";
    case FRAMESIZE_SXGA:  return "SXGA 1280x1024";
    case FRAMESIZE_UXGA:  return "UXGA 1600x1200";
    default:              return "resolution personnalisee";
  }
}

bool initCamera() {
  // ATTENTION : l'initialisation a zero n'est pas cosmetique. camera_config_t
  // contient des champs que ce fichier ne renseignait pas (fb_location,
  // grab_mode, sccb_i2c_port...). Declaree sans "= {}", la structure est posee
  // sur la pile avec ce qui s'y trouvait avant : esp_camera_init() lisait donc
  // des valeurs aleatoires, d'ou un buffer alloue au mauvais endroit et des
  // trames vides/noires de facon non reproductible.
  camera_config_t cfg = {};
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
  cfg.frame_size   = CAPTURE_FRAMESIZE;
  cfg.jpeg_quality = CAPTURE_JPEG_QUALITY;

  // Avec de la PSRAM : 2 buffers + GRAB_LATEST, pour que le capteur continue de
  // produire des trames pendant qu'on envoie la precedente (l'auto-exposition
  // reste ainsi a jour et la capture suivante est immediate). Sans PSRAM, on
  // reste sur 1 buffer en DRAM.
  if (psramFound()) {
    cfg.fb_location = CAMERA_FB_IN_PSRAM;
    cfg.fb_count    = 2;
    cfg.grab_mode   = CAMERA_GRAB_LATEST;
  } else {
    cfg.fb_location = CAMERA_FB_IN_DRAM;
    cfg.fb_count    = 1;
    cfg.grab_mode   = CAMERA_GRAB_WHEN_EMPTY;
    Serial.println("ATTENTION : PSRAM absente, capture en DRAM (1 buffer)");
  }

  if (esp_camera_init(&cfg) != ESP_OK) return false;
  // Auto-balance / exposition
  sensor_t* s = esp_camera_sensor_get();
  s->set_whitebal(s, 1);
  s->set_awb_gain(s, 1);
  s->set_exposure_ctrl(s, 1);
  s->set_gain_ctrl(s, 1);
  s->set_raw_gma(s, 1);
  s->set_lenc(s, 1);

  // Le framesize doit aussi etre force sur le capteur : selon les revisions de
  // l'OV2640, esp_camera_init() peut laisser le registre a sa valeur d'usine.
  s->set_framesize(s, CAPTURE_FRAMESIZE);

  Serial.printf("Resolution : %s (qualite JPEG %d)\n",
                framesizeLabel(CAPTURE_FRAMESIZE), CAPTURE_JPEG_QUALITY);
  return true;
}

// Jette WARMUP_FRAMES trames pour laisser l'auto-exposition converger, puis
// renvoie une trame exploitable — ou NULL. Sans ca, la premiere capture apres
// une periode d'inactivite sort noire.
static camera_fb_t* grabSettledFrame() {
  for (int i = 0; i < WARMUP_FRAMES; i++) {
    camera_fb_t* warm = esp_camera_fb_get();
    if (warm) esp_camera_fb_return(warm);
  }
  return esp_camera_fb_get();
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
#if USE_FLASH
  digitalWrite(LED_PIN, HIGH);
#endif
  camera_fb_t* fb = grabSettledFrame();
#if USE_FLASH
  digitalWrite(LED_PIN, LOW);
#endif
  if (!fb) {
    Serial.println("Capture ECHEC : aucune trame renvoyee par le capteur");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  // Ne jamais servir une trame que l'on sait deja invalide : le backend
  // refuserait le JPEG (verification SOI/EOI), mais autant dire ici pourquoi.
  // Un JPEG valide commence par FFD8 et se termine par FFD9.
  bool jpegOk = fb->len > 1000 &&
                fb->buf[0] == 0xFF && fb->buf[1] == 0xD8 &&
                fb->buf[fb->len - 2] == 0xFF && fb->buf[fb->len - 1] == 0xD9;
  if (!jpegOk) {
    Serial.printf("Capture INVALIDE : %u octets, JPEG incomplet\n", fb->len);
    esp_camera_fb_return(fb);
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "image/jpeg");
  httpd_resp_set_hdr(req, "Content-Disposition", "inline; filename=capture.jpg");
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-store");
  esp_err_t res = httpd_resp_send(req, (const char*)fb->buf, fb->len);
  Serial.printf("Capture OK : %u octets (%s)\n",
                fb->len, framesizeLabel(CAPTURE_FRAMESIZE));
  esp_camera_fb_return(fb);
  return res;
}

// ── GET /status ──────────────────────────────────────────────
static esp_err_t status_handler(httpd_req_t* req) {
  String ip = WiFi.localIP().toString();
  String json = "{\"status\":\"ok\",\"ip\":\"" + ip + "\""
                ",\"rssi\":" + String(WiFi.RSSI()) +
                ",\"framesize\":\"" + String(framesizeLabel(CAPTURE_FRAMESIZE)) + "\""
                ",\"heap\":" + String(ESP.getFreeHeap()) +
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
  // Un client qui abandonne une requete en cours (onglet ferme, timeout du
  // backend, WiFi qui hoquette) laisse un socket ouvert cote ESP32. Sans purge
  // LRU, ces sockets fantomes remplissent la table et le serveur finit par
  // refuser toute nouvelle connexion : la camera repond alors "injoignable"
  // alors qu'elle tourne parfaitement.
  cfg.lru_purge_enable = true;
  cfg.max_open_sockets = 4;
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
  scfg.lru_purge_enable = true;
  scfg.max_open_sockets = 2;
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

  // Mode station pur : sans ca l'ESP32 garde un SoftAP actif qui partage la
  // radio avec la station et degrade la liaison.
  WiFi.mode(WIFI_STA);

  // Le modem sleep est actif par defaut sur l'ESP32 : la radio s'endort entre
  // deux balises AP pour economiser du courant. La carte reste "connectee" au
  // sens WiFi.status(), mais les paquets entrants sont retardes ou perdus —
  // c'est ce qui fait qu'un test de connexion reussit puis que le suivant
  // echoue quelques secondes plus tard, sans que rien n'ait bouge.
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);

  // Evite d'user la flash en reecrivant les identifiants a chaque demarrage.
  WiFi.persistent(false);

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
  // Une micro-coupure WiFi (roaming, canal charge) est normale et se resorbe
  // en quelques secondes. Redemarrer des le premier echec de reconnexion
  // faisait perdre l'IP et coupait la camera pour ~10 s — bien plus long que
  // la coupure elle-meme. On laisse donc plusieurs tentatives avant de
  // considerer la liaison comme reellement perdue.
  static uint8_t echecs = 0;

  if (WiFi.status() != WL_CONNECTED) {
    echecs++;
    Serial.printf("WiFi perdu (tentative %u/6), reconnexion...\n", echecs);
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASS);

    for (int i = 0; i < 20 && WiFi.status() != WL_CONNECTED; i++) delay(500);

    if (WiFi.status() == WL_CONNECTED) {
      echecs = 0;
      Serial.print("WiFi retabli, IP : ");
      Serial.println(WiFi.localIP());
    } else if (echecs >= 6) {
      Serial.println("WiFi durablement perdu. Redemarrage...");
      delay(1000);
      ESP.restart();
    }
    return;
  }

  echecs = 0;
  delay(5000);
}
