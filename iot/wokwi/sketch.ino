/*
  VigIA · Poste inteligente (ESP32 no Wokwi)

  Sensores:
    - LDR (GPIO 34): mede a luz da lâmpada do poste
    - PIR (GPIO 27): detecta pessoas passando
    - Botão de pânico (GPIO 26): pedido de ajuda
  Atuador:
    - LED (GPIO 2): acende quando o pânico é acionado (sinal visual para quem está perto)

  A cada 10 segundos (ou na hora, se o botão for apertado) envia para a API:
    POST {API_URL}/sensores/leituras
    {"codigo_poste": "POSTE-001", "luz_ligada": true, "presenca": false, "panico": false}

  Para a API receber os dados, ela precisa estar acessível pela internet
  (ex.: ngrok http 8000). Veja iot/README.md. Sem isso, as leituras aparecem no Serial Monitor.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

// ---------------- configuração ----------------
const char* WIFI_REDE  = "Wokwi-GUEST";
const char* WIFI_SENHA = "";
const char* API_URL    = "https://SEU-ENDERECO.ngrok-free.app";  // troque pelo endereço do ngrok
const char* API_KEY    = "vigia-iot-dev";
const char* CODIGO     = "POSTE-001";

const int PINO_LDR   = 34;
const int PINO_PIR   = 27;
const int PINO_BOTAO = 26;
const int PINO_LED   = 2;

// No Wokwi, quanto MENOS luz, MAIOR o valor lido no LDR.
// Acima deste limite, consideramos a lâmpada apagada.
const int LIMITE_ESCURO = 2000;
const unsigned long INTERVALO_MS = 10000;

unsigned long ultimoEnvio = 0;

void conectarWifi() {
  Serial.print("Conectando ao Wi-Fi");
  WiFi.begin(WIFI_REDE, WIFI_SENHA);
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print(".");
  }
  Serial.println(" conectado!");
}

void enviarLeitura(bool luzLigada, bool presenca, bool panico) {
  String json = String("{\"codigo_poste\":\"") + CODIGO + "\"," +
                "\"luz_ligada\":" + (luzLigada ? "true" : "false") + "," +
                "\"presenca\":"   + (presenca ? "true" : "false") + "," +
                "\"panico\":"     + (panico ? "true" : "false") + "}";

  Serial.println("Leitura: " + json);

  if (WiFi.status() != WL_CONNECTED) {
    conectarWifi();
  }
  String url = String(API_URL) + "/sensores/leituras";
  HTTPClient http;
  WiFiClient clienteHttp;
  WiFiClientSecure clienteHttps;
  if (url.startsWith("https")) {
    clienteHttps.setInsecure();  // simulação: não valida o certificado do ngrok
    http.begin(clienteHttps, url);
  } else {
    http.begin(clienteHttp, url);
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-API-Key", API_KEY);
  http.addHeader("ngrok-skip-browser-warning", "1");
  int codigo = http.POST(json);
  Serial.printf("  API respondeu: %d\n", codigo);
  if (codigo > 0) {
    Serial.println("  " + http.getString());
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  pinMode(PINO_PIR, INPUT);
  pinMode(PINO_BOTAO, INPUT_PULLUP);  // botão liga o pino ao GND: apertado = LOW
  pinMode(PINO_LED, OUTPUT);
  conectarWifi();
}

void loop() {
  int valorLdr  = analogRead(PINO_LDR);
  bool luzLigada = valorLdr < LIMITE_ESCURO;
  bool presenca  = digitalRead(PINO_PIR) == HIGH;
  bool panico    = digitalRead(PINO_BOTAO) == LOW;

  digitalWrite(PINO_LED, panico ? HIGH : LOW);

  // Pânico é enviado na hora; o resto, a cada 10 segundos
  if (panico || millis() - ultimoEnvio >= INTERVALO_MS) {
    Serial.printf("LDR=%d ", valorLdr);
    enviarLeitura(luzLigada, presenca, panico);
    ultimoEnvio = millis();
    if (panico) {
      delay(1000);  // evita enviar várias vezes com um só aperto
    }
  }
  delay(100);
}
