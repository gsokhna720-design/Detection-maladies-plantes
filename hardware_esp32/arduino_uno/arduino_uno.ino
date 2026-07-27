// ============================================================
//  PlantAI — Arduino Uno : commande du servomoteur SG90 (pince)
//  Reçoit des ordres simples par liaison série USB (115200 bauds)
//  et actionne le servomoteur en conséquence.
//
//  Ce module n'a ni WiFi ni caméra : il est piloté en USB par un
//  hôte (PC / Raspberry Pi / ESP32 relié en série) qui décide quand
//  ouvrir/fermer la pince — par ex. après une analyse PlantAI positive.
//
//  Branchement SG90 :
//    Signal (orange) → pin 9 (PWM)
//    VCC (rouge)      → 5V (alimentation externe recommandée si plusieurs servos)
//    GND (marron)      → GND commun avec l'Arduino
//
//  Protocole série (une commande par ligne, terminée par '\n') :
//    "OUVRIR"        → position ouverte  (0°)
//    "FERMER"        → position fermée   (90°)
//    "ANGLE:<0-180>" → angle précis, ex. "ANGLE:45"
//
//  Réponse renvoyée sur le port série : "OK:<angle>" ou "ERR:<message>"
// ============================================================

#include <Servo.h>

#define SERVO_PIN 9

const int ANGLE_OUVERT = 0;
const int ANGLE_FERME  = 90;

Servo pince;
String buffer = "";

void appliquerAngle(int angle) {
  angle = constrain(angle, 0, 180);
  pince.write(angle);
  Serial.print("OK:");
  Serial.println(angle);
}

void traiterCommande(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "OUVRIR") {
    appliquerAngle(ANGLE_OUVERT);
  } else if (cmd == "FERMER") {
    appliquerAngle(ANGLE_FERME);
  } else if (cmd.startsWith("ANGLE:")) {
    int angle = cmd.substring(6).toInt();
    appliquerAngle(angle);
  } else if (cmd.length() > 0) {
    Serial.print("ERR:commande inconnue -> ");
    Serial.println(cmd);
  }
}

void setup() {
  Serial.begin(115200);
  pince.attach(SERVO_PIN);
  appliquerAngle(ANGLE_OUVERT);  // position de repos au démarrage
  Serial.println("=== PlantAI Arduino Uno — Servomoteur SG90 pret ===");
  Serial.println("Commandes : OUVRIR | FERMER | ANGLE:<0-180>");
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      traiterCommande(buffer);
      buffer = "";
    } else if (c != '\r') {
      buffer += c;
    }
  }
}
