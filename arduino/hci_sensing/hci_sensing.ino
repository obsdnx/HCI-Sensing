#include <Wire.h>

#define SDA_PIN   18
#define SCL_PIN    5
#define LSM_ADDR  0x6B

#define REG_WHO_AM_I  0x0F
#define REG_CTRL1_XL  0x10
#define REG_CTRL2_G   0x11
#define REG_CTRL3_C   0x12
#define REG_OUTX_L_G  0x22
#define REG_OUTX_L_XL 0x28

#define SAMPLE_HZ    100
#define DT           (1.0f / SAMPLE_HZ)
#define TAP_THRESH   2.8f   // g

// ── Madgwick ─────────────────────────────────────────────────────────────────

float mq0=1, mq1=0, mq2=0, mq3=0;
const float BETA = 0.08f;

void madgwickUpdate(float gx, float gy, float gz,
                    float ax, float ay, float az) {
  gx *= DEG_TO_RAD; gy *= DEG_TO_RAD; gz *= DEG_TO_RAD;

  float norm = sqrtf(ax*ax + ay*ay + az*az);
  if (norm < 1e-10f) return;
  ax /= norm; ay /= norm; az /= norm;

  float q0=mq0, q1=mq1, q2=mq2, q3=mq3;

  float s0 = 4*q0*q2*q2 + 2*q2*ax + 4*q0*q1*q1 - 2*q1*ay;
  float s1 = 4*q1*q3*q3 - 2*q3*ax + 4*q0*q0*q1 - 2*q0*ay
             - 4*q1 + 8*q1*q1*q1 + 8*q1*q2*q2 + 4*q1*az;
  float s2 = 4*q0*q0*q2 + 2*q0*ax + 4*q2*q3*q3 - 2*q3*ay
             - 4*q2 + 8*q2*q1*q1 + 8*q2*q2*q2 + 4*q2*az;
  float s3 = 4*q1*q1*q3 - 2*q1*ax + 4*q2*q2*q3 - 2*q2*ay;

  norm = sqrtf(s0*s0 + s1*s1 + s2*s2 + s3*s3);
  if (norm > 0) { s0/=norm; s1/=norm; s2/=norm; s3/=norm; }

  mq0 += (0.5f*(-q1*gx-q2*gy-q3*gz) - BETA*s0) * DT;
  mq1 += (0.5f*( q0*gx+q2*gz-q3*gy) - BETA*s1) * DT;
  mq2 += (0.5f*( q0*gy-q1*gz+q3*gx) - BETA*s2) * DT;
  mq3 += (0.5f*( q0*gz+q1*gy-q2*gx) - BETA*s3) * DT;

  norm = sqrtf(mq0*mq0+mq1*mq1+mq2*mq2+mq3*mq3);
  mq0/=norm; mq1/=norm; mq2/=norm; mq3/=norm;
}

void getEuler(float &roll, float &pitch) {
  roll  = atan2f(2*(mq0*mq1+mq2*mq3), 1-2*(mq1*mq1+mq2*mq2)) * RAD_TO_DEG;
  pitch = asinf(constrain(2*(mq0*mq2-mq3*mq1), -1.0f, 1.0f))  * RAD_TO_DEG;
}

// ── I2C helpers ───────────────────────────────────────────────────────────────

void writeReg(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(LSM_ADDR);
  Wire.write(reg); Wire.write(val);
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

// ── Setup ─────────────────────────────────────────────────────────────────────

void setup() {
  Serial.begin(460800);
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);

  uint8_t who = readReg(REG_WHO_AM_I);
  if (who != 0x69) {
    Serial.println("LSM6DS3 not found");
    while (1);
  }

  writeReg(REG_CTRL3_C,  0x04);
  writeReg(REG_CTRL1_XL, 0x40);  // accel 104 Hz ±2g
  writeReg(REG_CTRL2_G,  0x40);  // gyro  104 Hz ±245°/s

  Serial.println("t_ms,ax,ay,az,gx,gy,gz,roll,pitch,tap");
}

// ── Loop ──────────────────────────────────────────────────────────────────────

float prevMag = 1.0f;
unsigned long lastTap = 0;

void loop() {
  unsigned long t0 = millis();
  uint8_t buf[6];

  readBytes(REG_OUTX_L_G, buf, 6);
  float gx = (int16_t)(buf[1]<<8|buf[0]) * 0.00875f;
  float gy = (int16_t)(buf[3]<<8|buf[2]) * 0.00875f;
  float gz = (int16_t)(buf[5]<<8|buf[4]) * 0.00875f;

  readBytes(REG_OUTX_L_XL, buf, 6);
  float ax = (int16_t)(buf[1]<<8|buf[0]) / 16393.0f;
  float ay = (int16_t)(buf[3]<<8|buf[2]) / 16393.0f;
  float az = (int16_t)(buf[5]<<8|buf[4]) / 16393.0f;

  madgwickUpdate(gx, gy, gz, ax, ay, az);

  float roll, pitch;
  getEuler(roll, pitch);

  // Tap detection: spike from near-1g past threshold
  float mag = sqrtf(ax*ax + ay*ay + az*az);
  uint8_t tap = 0;
  if (prevMag < 1.5f && mag > TAP_THRESH && (millis()-lastTap) > 500) {
    tap = 1;
    lastTap = millis();
  }
  prevMag = mag;

  Serial.print(millis()); Serial.print(',');
  Serial.print(ax,4); Serial.print(',');
  Serial.print(ay,4); Serial.print(',');
  Serial.print(az,4); Serial.print(',');
  Serial.print(gx,4); Serial.print(',');
  Serial.print(gy,4); Serial.print(',');
  Serial.print(gz,4); Serial.print(',');
  Serial.print(roll,2); Serial.print(',');
  Serial.print(pitch,2); Serial.print(',');
  Serial.println(tap);

  // Hold 100 Hz
  long elapsed = millis() - t0;
  if (elapsed < 10) delay(10 - elapsed);
}
