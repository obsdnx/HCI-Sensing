#include <Wire.h>

#define SDA_PIN   18
#define SCL_PIN    5
#define LSM_ADDR  0x6A

#define REG_WHO_AM_I  0x0F
#define REG_CTRL1_XL  0x10   // accel config
#define REG_CTRL2_G   0x11   // gyro config
#define REG_CTRL3_C   0x12   // auto-increment enable
#define REG_OUTX_L_G  0x22   // gyro output start
#define REG_OUTX_L_XL 0x28   // accel output start

void writeReg(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(LSM_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

uint8_t readReg(uint8_t reg) {
  Wire.beginTransmission(LSM_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(LSM_ADDR, 1);
  return Wire.read();
}

void readBytes(uint8_t reg, uint8_t *buf, uint8_t len) {
  Wire.beginTransmission(LSM_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(LSM_ADDR, len);
  for (uint8_t i = 0; i < len; i++) buf[i] = Wire.read();
}

void setup() {
  Serial.begin(115200);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);

  uint8_t who = readReg(REG_WHO_AM_I);
  Serial.print("WHO_AM_I: 0x");
  Serial.println(who, HEX);  // expect 0x69

  if (who != 0x69) {
    Serial.println("LSM6DS3 not found — check wiring");
    while (1);
  }

  writeReg(REG_CTRL3_C,  0x04);  // auto-increment on
  writeReg(REG_CTRL1_XL, 0x40);  // accel: 104 Hz, ±2g
  writeReg(REG_CTRL2_G,  0x40);  // gyro:  104 Hz, ±245°/s

  Serial.println("t_ms,ax,ay,az,gx,gy,gz");
}

void loop() {
  uint8_t buf[6];

  // Gyro
  readBytes(REG_OUTX_L_G, buf, 6);
  int16_t gx_raw = (int16_t)(buf[1] << 8 | buf[0]);
  int16_t gy_raw = (int16_t)(buf[3] << 8 | buf[2]);
  int16_t gz_raw = (int16_t)(buf[5] << 8 | buf[4]);

  // Accel
  readBytes(REG_OUTX_L_XL, buf, 6);
  int16_t ax_raw = (int16_t)(buf[1] << 8 | buf[0]);
  int16_t ay_raw = (int16_t)(buf[3] << 8 | buf[2]);
  int16_t az_raw = (int16_t)(buf[5] << 8 | buf[4]);

  // Convert
  float ax = ax_raw / 16393.0;
  float ay = ay_raw / 16393.0;
  float az = az_raw / 16393.0;
  float gx = gx_raw * 0.00875;
  float gy = gy_raw * 0.00875;
  float gz = gz_raw * 0.00875;

  Serial.print(millis());
  Serial.print(",");
  Serial.print(ax, 4); Serial.print(",");
  Serial.print(ay, 4); Serial.print(",");
  Serial.print(az, 4); Serial.print(",");
  Serial.print(gx, 4); Serial.print(",");
  Serial.print(gy, 4); Serial.print(",");
  Serial.println(gz, 4);

  delay(10);  // 100 Hz
}
