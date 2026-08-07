#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BME280.h>
#include "time.h"
#include "secrets.h"

Adafruit_BME280 bme;


// --- Moisture sensor ---
const int moisturePin = 35;
const int dryValue = 2800;
const int wetValue = 1090;

// --- Time ---
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = -6 * 3600;   // Central Standard Time
const int daylightOffset_sec = 3600;    // Daylight Saving Time

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

  // --- WiFi ---
  WiFi.disconnect(true);
  delay(1000);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);;

  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("WiFi connected!");

  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  // --- NTP time ---
  configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);

  Serial.println("Time synchronization requested.");
  Serial.println();
}

void loop() {
  // --- Time ---
  struct tm timeinfo;

  if (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to obtain time");
  }

  // --- Moisture ---
  int rawMoisture = analogRead(moisturePin);

  float moisturePercent =
      (dryValue - rawMoisture) * 100.0 /
      (dryValue - wetValue);

  moisturePercent = constrain(moisturePercent, 0.0, 100.0);

  // --- BME280 ---
  float temperature = bme.readTemperature();
  float humidity = bme.readHumidity();
  float pressure = bme.readPressure() / 100.0F;

  // --- Output ---
  Serial.println("========== BackyardOS ==========");

  if (getLocalTime(&timeinfo)) {
    Serial.print("Timestamp: ");
    Serial.println(&timeinfo, "%Y-%m-%d %H:%M:%S");
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

  delay(10000);
}