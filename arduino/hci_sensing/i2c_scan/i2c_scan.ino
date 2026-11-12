#include <Wire.h>

#define SDA_PIN 18
#define SCL_PIN  5

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(100000);  // slower speed for debugging
  delay(1000);

  Serial.println("Scanning I2C bus...");
  int found = 0;
  for (int addr = 1; addr < 127; addr++) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      Serial.print("Found device at 0x");
      Serial.println(addr, HEX);
      found++;
    }
  }
  if (found == 0) Serial.println("No devices found");
  Serial.println("Done.");
}

void loop() {}
