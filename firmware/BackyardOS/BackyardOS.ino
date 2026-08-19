#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include "time.h"
#include "secrets.h"
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

Adafruit_BME280 bme;


// --- Moisture sensor ---
const int moisturePin = 35;
const int dryValue = 2800;
const int wetValue = 1090;


// --- Time ---
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = -6 * 3600;
const int daylightOffset_sec = 3600;


// --- WiFi event logging ---
void onWiFiEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
  if (event == ARDUINO_EVENT_WIFI_STA_DISCONNECTED) {
    Serial.print("WiFi disconnect reason code: ");
    Serial.println(info.wifi_sta_disconnected.reason);
  }
}


// --- WiFi connection / recovery ---
bool connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    return true;
  }

  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttemptTime = millis();
  const unsigned long wifiTimeout = 10000;

  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - startAttemptTime < wifiTimeout
  ) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected!");

    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

    Serial.print("RSSI: ");
    Serial.println(WiFi.RSSI());

    return true;
  }

  Serial.println("WiFi connection FAILED.");
  return false;
}


// --- Send reading to Render API ---
void sendReading(
  int rawMoisture,
  float moisturePercent,
  float temperature,
  float humidity,
  float pressure,
  struct tm timeinfo
) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected. Skipping POST.");
    return;
  }

  char timestamp[25];

  strftime(
    timestamp,
    sizeof(timestamp),
    "%Y-%m-%dT%H:%M:%S",
    &timeinfo
  );

  String jsonPayload = "{";
  jsonPayload += "\"device_id\":\"backyard-node-01\",";
  jsonPayload += "\"timestamp\":\"" + String(timestamp) + "\",";
  jsonPayload += "\"soil_moisture_raw\":" + String(rawMoisture) + ",";
  jsonPayload += "\"soil_moisture_pct\":" + String(moisturePercent, 1) + ",";
  jsonPayload += "\"temperature_c\":" + String(temperature, 2) + ",";
  jsonPayload += "\"humidity_pct\":" + String(humidity, 2) + ",";
  jsonPayload += "\"pressure_hpa\":" + String(pressure, 2);
  jsonPayload += "}";

  const int maxAttempts = 3;

  for (int attempt = 1; attempt <= maxAttempts; attempt++) {

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("WiFi lost during POST attempts.");
      return;
    }

    Serial.print("POST attempt ");
    Serial.print(attempt);
    Serial.print(" of ");
    Serial.println(maxAttempts);

    WiFiClientSecure client;
    client.setInsecure();

    HTTPClient http;

    http.begin(
      client,
      "https://backyardos.onrender.com/readings"
    );

    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-API-Key", API_KEY);

    int httpResponseCode = http.POST(jsonPayload);

    Serial.print("POST response code: ");
    Serial.println(httpResponseCode);

    if (httpResponseCode >= 200 && httpResponseCode < 300) {
      String response = http.getString();

      Serial.print("Server response: ");
      Serial.println(response);

      http.end();

      Serial.println("POST successful.");
      return;
    }

    Serial.print("POST failed: ");
    Serial.println(http.errorToString(httpResponseCode));

    http.end();

    if (attempt < maxAttempts) {
      Serial.println("Retrying in 2 seconds...");
      delay(2000);
    }
  }

  Serial.println("POST failed after 3 attempts.");
}


void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("Starting BackyardOS...");


  // --- BME280 ---
  if (!bme.begin(0x76)) {
    Serial.println("BME280 not found!");

    while (true) {
      delay(1000);
    }
  }

  Serial.println("BME280 connected.");


  // --- WiFi event listener ---
  WiFi.onEvent(onWiFiEvent);


  // --- Initial WiFi connection ---
  bool wifiConnected = connectWiFi();


  // --- NTP time ---
  if (wifiConnected) {
    configTime(
      gmtOffset_sec,
      daylightOffset_sec,
      ntpServer
    );

    Serial.println("Time synchronization requested.");
  } else {
    Serial.println("Skipping NTP setup because WiFi is not connected.");
  }

  Serial.println();
}


void loop() {

  // --- WiFi recovery ---
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi connection lost. Attempting reconnect...");

    bool reconnected = connectWiFi();

    if (reconnected) {
      configTime(
        gmtOffset_sec,
        daylightOffset_sec,
        ntpServer
      );

      Serial.println("Time synchronization requested after reconnect.");
    }
  }


  // --- Time ---
  struct tm timeinfo;

  bool timeAvailable = false;

  if (WiFi.status() == WL_CONNECTED) {
    timeAvailable = getLocalTime(&timeinfo);
  }

  if (!timeAvailable) {
    Serial.println("Time unavailable.");
  }


  // --- Moisture ---
  int rawMoisture = analogRead(moisturePin);

  float moisturePercent =
      (dryValue - rawMoisture) * 100.0 /
      (dryValue - wetValue);

  moisturePercent =
      constrain(moisturePercent, 0.0, 100.0);


  // --- BME280 ---
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;


  // --- Output ---
  Serial.println("========== BackyardOS ==========");

  if (timeAvailable) {
    Serial.print("Timestamp: ");
    Serial.println(
      &timeinfo,
      "%Y-%m-%d %H:%M:%S"
    );
  }

  Serial.print("Soil Moisture Raw: ");
  Serial.println(rawMoisture);

  Serial.print("Soil Moisture: ");
  Serial.print(moisturePercent, 1);
  Serial.println(" %");

  Serial.print("Temperature: ");
  Serial.print(temperature, 2);
  Serial.println(" C");

  Serial.print("Humidity: ");
  Serial.print(humidity, 2);
  Serial.println(" %");

  Serial.print("Pressure: ");
  Serial.print(pressure, 2);
  Serial.println(" hPa");

  Serial.println("================================");
  Serial.println();


  // --- Send reading to API ---
  if (timeAvailable) {
    sendReading(
      rawMoisture,
      moisturePercent,
      temperature,
      humidity,
      pressure,
      timeinfo
    );
  } else {
    Serial.println("Skipping POST because time is unavailable.");
  }

  Serial.println();

  delay(600000);
}