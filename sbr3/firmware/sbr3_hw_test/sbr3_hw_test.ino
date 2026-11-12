/*
  SBR3 hardware bring-up test (ESP32-S3-DevKitC-1 main board)

  Tests every block of the SBR3 board one by one from a Serial menu (115200 baud):
    1  Status LED (IO17)              5  IMU GY-9250 / MPU-9250 (I2C IO8/IO9, INT IO10)
    2  Buzzer (IO16, via MMBT3904)    6  Eyes: 2x MAX7219 through 74AHCT125 (DIN IO11, CLK IO12, CS IO13/IO14)
    3  User button (IO18)             7  Left motor  (A4988 #1: STEP IO4, DIR IO5)
    4  Battery voltage (IO1 ADC)      8  Right motor (A4988 #2: STEP IO6, DIR IO7)
                                      9  Both motors together (shared ENABLE IO15)
    a  run the automatic tests (1-6), then print a PASS/FAIL summary

  Only the Arduino-ESP32 core is needed (Wire, SPI). Board: "ESP32S3 Dev Module".
  Motor tests turn the wheels: lift the robot first. The soft-start needs ~0.5 s after power-on before
  the A4988s may be enabled; this sketch waits at least 1 s.
*/
#include <Arduino.h>
#include <SPI.h>
#include <Wire.h>

// ---------------------------------------------------------------- SBR3 pin map (schematic modules/Mcu.zen)
constexpr int PIN_M1_STEP = 4;   // MOTOR_LEFT  A4988 STEP
constexpr int PIN_M1_DIR = 5;    // MOTOR_LEFT  A4988 DIR
constexpr int PIN_M2_STEP = 6;   // MOTOR_RIGHT A4988 STEP
constexpr int PIN_M2_DIR = 7;    // MOTOR_RIGHT A4988 DIR
constexpr int PIN_MOT_EN_N = 15; // both A4988 ~ENABLE, pulled high on the board (= disabled)
constexpr int PIN_SDA = 8;
constexpr int PIN_SCL = 9;
constexpr int PIN_IMU_INT = 10;
constexpr int PIN_MAX_DIN = 11;  // 3.3 V side of the 74AHCT125
constexpr int PIN_MAX_CLK = 12;
constexpr int PIN_MAX_CS_L = 13;
constexpr int PIN_MAX_CS_R = 14;
constexpr int PIN_BUZZER = 16;
constexpr int PIN_STATUS_LED = 17;
constexpr int PIN_BUTTON = 18;   // active low, 10k pull-up + 100 nF on the board
constexpr int PIN_VBAT = 1;      // ADC1_CH0, VMOT * 22k / (100k + 22k)

// ---------------------------------------------------------------- hardware constants
constexpr float VBAT_DIVIDER = (100.0f + 22.0f) / 22.0f;
constexpr float VBAT_FET_DROP = 0.05f;      // fuse + soft-start FET pair at light load
constexpr float VBAT_MIN_OK = 9.0f;         // 3S at 3.0 V/cell
constexpr float VBAT_MAX_OK = 13.3f;        // 3S LiPo full 12.6 V, 3S LiHV (CODDAR CD3S115060HV) full 13.05 V
constexpr int STEPS_PER_REV = 200 * 16;     // 1.8 deg motor, MS1-3 high = 1/16 step
constexpr uint8_t MPU_ADDR = 0x68;          // AD0 tied low
constexpr uint8_t AK8963_ADDR = 0x0C;

enum Result : uint8_t { R_NONE, R_PASS, R_FAIL, R_SKIP };
const char *resultName(Result r) {
  switch (r) {
    case R_PASS: return "PASS";
    case R_FAIL: return "FAIL";
    case R_SKIP: return "SKIP";
    default: return "-";
  }
}
Result results[10];
const char *testNames[10] = {"", "Status LED", "Buzzer", "Button", "Battery ADC", "IMU", "Eyes (MAX7219)",
                             "Left motor", "Right motor", "Both motors"};

// ---------------------------------------------------------------- serial helpers
void flushInput() {
  delay(20);
  while (Serial.available()) Serial.read();
}

// Waits for a y/n answer; returns false on 'n' or after timeout_ms.
bool askYesNo(const char *question, uint32_t timeout_ms = 30000) {
  flushInput();
  Serial.printf("%s [y/n] ", question);
  uint32_t t0 = millis();
  while (millis() - t0 < timeout_ms) {
    if (Serial.available()) {
      char c = tolower(Serial.read());
      if (c == 'y') { Serial.println("y"); return true; }
      if (c == 'n') { Serial.println("n"); return false; }
    }
    delay(5);
  }
  Serial.println("(timeout)");
  return false;
}

// ---------------------------------------------------------------- 1. status LED
Result testStatusLed() {
  Serial.println("\n[1] Status LED (IO17, blue, 330R): blinking 5x");
  for (int i = 0; i < 5; i++) {
    digitalWrite(PIN_STATUS_LED, HIGH);
    delay(200);
    digitalWrite(PIN_STATUS_LED, LOW);
    delay(200);
  }
  return askYesNo("Did the blue status LED blink 5 times?") ? R_PASS : R_FAIL;
}

// ---------------------------------------------------------------- 2. buzzer
Result testBuzzer() {
  Serial.println("\n[2] Buzzer (IO16 -> MMBT3904, active 5 V buzzer): 3 beeps");
  for (int i = 0; i < 3; i++) {
    digitalWrite(PIN_BUZZER, HIGH);
    delay(120);
    digitalWrite(PIN_BUZZER, LOW);
    delay(200);
  }
  return askYesNo("Did you hear 3 beeps?") ? R_PASS : R_FAIL;
}

// ---------------------------------------------------------------- 3. button
Result testButton() {
  Serial.println("\n[3] User button (IO18, active low)");
  if (digitalRead(PIN_BUTTON) == LOW) {
    Serial.println("  FAIL: IO18 reads LOW while released (short to GND or missing pull-up R)");
    return R_FAIL;
  }
  Serial.println("  Press and release the button within 10 s...");
  uint32_t t0 = millis();
  while (digitalRead(PIN_BUTTON) == HIGH) {
    if (millis() - t0 > 10000) {
      Serial.println("  FAIL: no press detected");
      return R_FAIL;
    }
    delay(1);
  }
  uint32_t tPress = millis();
  Serial.println("  pressed");
  while (digitalRead(PIN_BUTTON) == LOW) {
    if (millis() - tPress > 10000) {
      Serial.println("  FAIL: still LOW after 10 s (stuck)");
      return R_FAIL;
    }
    delay(1);
  }
  Serial.printf("  released after %lu ms\n", (unsigned long)(millis() - tPress));
  return R_PASS;
}

// ---------------------------------------------------------------- 4. battery ADC
float readVmot() {
  uint32_t sum = 0;
  for (int i = 0; i < 32; i++) sum += analogReadMilliVolts(PIN_VBAT);
  return (sum / 32.0f) / 1000.0f * VBAT_DIVIDER;
}

Result testBattery() {
  Serial.println("\n[4] Battery sense (IO1, 100k/22k divider on VMOT)");
  float vmot = readVmot();
  float vbat = vmot + VBAT_FET_DROP;
  Serial.printf("  VBAT_SENSE = %.3f V  ->  VMOT = %.2f V, battery ~ %.2f V (%.2f V/cell)\n",
                vmot / VBAT_DIVIDER, vmot, vbat, vbat / 3.0f);
  if (vmot < 1.0f) {
    Serial.println("  SKIP: no battery (board powered from USB only)");
    return R_SKIP;
  }
  if (vbat < VBAT_MIN_OK || vbat > VBAT_MAX_OK) {
    Serial.printf("  FAIL: outside %.1f..%.1f V (check divider R / battery)\n", VBAT_MIN_OK, VBAT_MAX_OK);
    return R_FAIL;
  }
  return R_PASS;
}

// ---------------------------------------------------------------- 5. IMU (MPU-9250 + AK8963)
bool i2cWrite(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

bool i2cRead(uint8_t addr, uint8_t reg, uint8_t *buf, size_t n) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, (uint8_t)n) != n) return false;
  for (size_t i = 0; i < n; i++) buf[i] = Wire.read();
  return true;
}

volatile uint32_t imuIntCount = 0;
void IRAM_ATTR onImuInt() { imuIntCount = imuIntCount + 1; }

Result testImu() {
  Serial.println("\n[5] IMU GY-9250 (MPU-9250 @0x68, AK8963 @0x0C)");
  Serial.print("  I2C scan:");
  int found = 0;
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) {
      Serial.printf(" 0x%02X", a);
      found++;
    }
  }
  Serial.println(found ? "" : " nothing (check SDA/SCL, IMU power, pull-ups)");

  uint8_t who = 0;
  if (!i2cRead(MPU_ADDR, 0x75, &who, 1)) {
    Serial.println("  FAIL: no answer from 0x68 (AD0 must be low, VCC 3.3 V)");
    return R_FAIL;
  }
  const char *chip = who == 0x71 ? "MPU-9250" : who == 0x73 ? "MPU-9255" : who == 0x70 ? "MPU-6500 (no magnetometer!)" : "unknown";
  Serial.printf("  WHO_AM_I = 0x%02X (%s)\n", who, chip);
  if (who != 0x71 && who != 0x73 && who != 0x70) return R_FAIL;

  i2cWrite(MPU_ADDR, 0x6B, 0x80);  // PWR_MGMT_1: reset
  delay(100);
  i2cWrite(MPU_ADDR, 0x6B, 0x01);  // clock = PLL
  i2cWrite(MPU_ADDR, 0x1A, 0x03);  // CONFIG: DLPF 41 Hz
  i2cWrite(MPU_ADDR, 0x19, 0x09);  // SMPLRT_DIV: 1 kHz / 10 = 100 Hz
  i2cWrite(MPU_ADDR, 0x1B, 0x00);  // GYRO_CONFIG: +/-250 dps
  i2cWrite(MPU_ADDR, 0x1C, 0x00);  // ACCEL_CONFIG: +/-2 g
  i2cWrite(MPU_ADDR, 0x37, 0x02);  // INT_PIN_CFG: active-high 50 us pulse, I2C bypass for the AK8963
  i2cWrite(MPU_ADDR, 0x38, 0x01);  // INT_ENABLE: raw data ready
  delay(50);

  // Average 50 samples with the robot standing still.
  double ax = 0, ay = 0, az = 0, gx = 0, gy = 0, gz = 0, tc = 0;
  const int N = 50;
  for (int i = 0; i < N; i++) {
    uint8_t b[14];
    if (!i2cRead(MPU_ADDR, 0x3B, b, 14)) {
      Serial.println("  FAIL: data read error");
      return R_FAIL;
    }
    ax += (int16_t)(b[0] << 8 | b[1]) / 16384.0;
    ay += (int16_t)(b[2] << 8 | b[3]) / 16384.0;
    az += (int16_t)(b[4] << 8 | b[5]) / 16384.0;
    tc += (int16_t)(b[6] << 8 | b[7]) / 333.87 + 21.0;
    gx += (int16_t)(b[8] << 8 | b[9]) / 131.0;
    gy += (int16_t)(b[10] << 8 | b[11]) / 131.0;
    gz += (int16_t)(b[12] << 8 | b[13]) / 131.0;
    delay(10);
  }
  ax /= N; ay /= N; az /= N; gx /= N; gy /= N; gz /= N; tc /= N;
  double g = sqrt(ax * ax + ay * ay + az * az);
  double pitch = atan2(ax, sqrt(ay * ay + az * az)) * 180.0 / PI;
  double roll = atan2(ay, az) * 180.0 / PI;
  Serial.printf("  accel  x=%+.3f y=%+.3f z=%+.3f g   |a|=%.3f g\n", ax, ay, az, g);
  Serial.printf("  gyro   x=%+.2f y=%+.2f z=%+.2f dps (bias at rest)\n", gx, gy, gz);
  Serial.printf("  pitch %+.1f deg, roll %+.1f deg, die temp %.1f C\n", pitch, roll, tc);
  bool ok = true;
  if (g < 0.85 || g > 1.15) {
    Serial.println("  FAIL: |a| should be ~1 g at rest");
    ok = false;
  }
  if (fabs(gx) > 10 || fabs(gy) > 10 || fabs(gz) > 10) {
    Serial.println("  FAIL: gyro bias > 10 dps (robot moving, or sensor damaged)");
    ok = false;
  }

  // Interrupt line IMU_INT (IO10): expect ~100 data-ready pulses per second.
  imuIntCount = 0;
  attachInterrupt(digitalPinToInterrupt(PIN_IMU_INT), onImuInt, RISING);
  delay(500);
  detachInterrupt(digitalPinToInterrupt(PIN_IMU_INT));
  uint8_t st;
  i2cRead(MPU_ADDR, 0x3A, &st, 1);
  Serial.printf("  INT pin: %lu pulses in 0.5 s (expected ~50)\n", (unsigned long)imuIntCount);
  if (imuIntCount < 30 || imuIntCount > 70) {
    Serial.println("  FAIL: INT line not toggling (check IMU INT -> IO10)");
    ok = false;
  }

  // Magnetometer through the bypass.
  if (who != 0x70) {
    uint8_t wia = 0;
    if (i2cRead(AK8963_ADDR, 0x00, &wia, 1) && wia == 0x48) {
      i2cWrite(AK8963_ADDR, 0x0A, 0x16);  // CNTL1: 16-bit, continuous mode 2 (100 Hz)
      delay(50);
      uint8_t m[7];
      if (i2cRead(AK8963_ADDR, 0x03, m, 7)) {  // HXL..HZH + ST2 (reading ST2 releases the data)
        int16_t mx = m[1] << 8 | m[0], my = m[3] << 8 | m[2], mz = m[5] << 8 | m[4];
        Serial.printf("  magnetometer AK8963 OK, raw x=%d y=%d z=%d (0.15 uT/LSB)\n", mx, my, mz);
      }
    } else {
      Serial.printf("  WARN: AK8963 not found (WIA=0x%02X) - clone chip without magnetometer?\n", wia);
    }
  }
  return ok ? R_PASS : R_FAIL;
}

// ---------------------------------------------------------------- 6. eyes: two MAX7219, separate CS
void maxWrite(int cs, uint8_t reg, uint8_t val) {
  SPI.beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE0));
  digitalWrite(cs, LOW);
  SPI.transfer(reg);
  SPI.transfer(val);
  digitalWrite(cs, HIGH);
  SPI.endTransaction();
}

void maxInit(int cs) {
  maxWrite(cs, 0x0F, 0x00);  // display test off
  maxWrite(cs, 0x09, 0x00);  // no BCD decode (matrix)
  maxWrite(cs, 0x0A, 0x02);  // intensity 2/15 (same as the SBR firmware)
  maxWrite(cs, 0x0B, 0x07);  // scan all 8 rows
  maxWrite(cs, 0x0C, 0x01);  // normal operation
}

void maxShow(int cs, const uint8_t rows[8]) {
  for (uint8_t r = 0; r < 8; r++) maxWrite(cs, r + 1, rows[r]);
}

const uint8_t EYE_L[8] = {0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0x80, 0xFE};  // letter "L"
const uint8_t EYE_R[8] = {0xFC, 0x82, 0x82, 0xFC, 0x90, 0x88, 0x84, 0x82};  // letter "R"
const uint8_t EYE_OPEN[8] = {0x3C, 0x7E, 0xFF, 0xFF, 0xFF, 0xFF, 0x7E, 0x3C};
const uint8_t EYE_BLANK[8] = {0};

Result testEyes() {
  Serial.println("\n[6] Eyes: MAX7219 x2 (DIN IO11, CLK IO12, CS_L IO13, CS_R IO14) via 74AHCT125");
  maxInit(PIN_MAX_CS_L);
  maxInit(PIN_MAX_CS_R);
  Serial.println("  Both eyes: display-test (all LEDs on) for 1 s");
  maxWrite(PIN_MAX_CS_L, 0x0F, 0x01);
  maxWrite(PIN_MAX_CS_R, 0x0F, 0x01);
  delay(1000);
  maxWrite(PIN_MAX_CS_L, 0x0F, 0x00);
  maxWrite(PIN_MAX_CS_R, 0x0F, 0x00);
  maxShow(PIN_MAX_CS_L, EYE_BLANK);
  maxShow(PIN_MAX_CS_R, EYE_BLANK);
  bool allOn = askYesNo("Did ALL 64 LEDs of BOTH eyes light up?");

  // Only the left CS: an "L" must appear on the left eye and nothing on the right one.
  maxShow(PIN_MAX_CS_L, EYE_L);
  bool left = askYesNo("Is there an 'L' on the LEFT eye only (right eye dark)?");
  maxShow(PIN_MAX_CS_L, EYE_BLANK);
  maxShow(PIN_MAX_CS_R, EYE_R);
  bool right = askYesNo("Is there an 'R' on the RIGHT eye only (left eye dark)?");
  maxShow(PIN_MAX_CS_L, EYE_OPEN);
  maxShow(PIN_MAX_CS_R, EYE_OPEN);
  if (!allOn) Serial.println("  hint: no LEDs at all -> check +5V on J1/J2 pin 1, 74AHCT125 power");
  if (allOn && !(left && right)) Serial.println("  hint: wrong eye answers -> CS_L/CS_R swapped or a CS line open");
  return (allOn && left && right) ? R_PASS : R_FAIL;
}

// ---------------------------------------------------------------- 7-9. stepper motors
void motorsEnable(bool on) { digitalWrite(PIN_MOT_EN_N, on ? LOW : HIGH); }

// Trapezoidal move of one or both motors; steps > 0 forward.
void stepMotors(bool left, bool right, long steps, float maxStepsPerSec) {
  bool fwd = steps > 0;
  steps = labs(steps);
  digitalWrite(PIN_M1_DIR, fwd ? HIGH : LOW);
  digitalWrite(PIN_M2_DIR, fwd ? LOW : HIGH);  // right motor is mirrored on the chassis
  delayMicroseconds(5);
  const float minRate = 400.0f, accel = 8000.0f;  // steps/s, steps/s^2
  float rate = minRate;
  for (long i = 0; i < steps; i++) {
    long remaining = steps - i;
    float stopDist = (rate * rate - minRate * minRate) / (2 * accel);
    if (remaining <= stopDist) rate = max(minRate, rate - accel / rate);
    else if (rate < maxStepsPerSec) rate = min(maxStepsPerSec, rate + accel / rate);
    uint32_t half = (uint32_t)(500000.0f / rate);
    if (left) digitalWrite(PIN_M1_STEP, HIGH);
    if (right) digitalWrite(PIN_M2_STEP, HIGH);
    delayMicroseconds(half);
    digitalWrite(PIN_M1_STEP, LOW);
    digitalWrite(PIN_M2_STEP, LOW);
    delayMicroseconds(half);
  }
}

Result testMotor(int which) {  // 0 left, 1 right, 2 both
  const char *label = which == 0 ? "LEFT" : which == 1 ? "RIGHT" : "BOTH";
  Serial.printf("\n[%d] %s motor(s): 1 turn forward, 1 turn back (1/16 step, %d steps/rev)\n", 7 + which, label, STEPS_PER_REV);
  if (readVmot() < 8.0f) {
    Serial.println("  SKIP: VMOT < 8 V - connect and switch on the battery (A4988 needs 8-35 V)");
    return R_SKIP;
  }
  if (!askYesNo("Robot lifted / wheels free to spin?")) return R_SKIP;
  while (millis() < 1000) delay(10);  // soft-start gate must be fully on before the motors load VMOT
  float vIdle = readVmot();
  motorsEnable(true);
  delay(20);
  stepMotors(which != 1, which != 0, STEPS_PER_REV, 3200);
  float vLoad = readVmot();
  delay(300);
  stepMotors(which != 1, which != 0, -STEPS_PER_REV, 3200);
  motorsEnable(false);
  Serial.printf("  VMOT idle %.2f V, while stepping %.2f V (sag %.2f V)\n", vIdle, vLoad, vIdle - vLoad);
  if (vIdle - vLoad > 1.0f) Serial.println("  WARN: large VMOT sag - weak battery, PTC heating or soft-start FET not fully on");
  bool ok = askYesNo(which == 2 ? "Did both wheels turn one revolution forward and back, smoothly?"
                                : "Did that wheel turn one revolution forward and back, smoothly?");
  if (!ok) Serial.println("  hint: buzzing but not turning -> coil pairs swapped (J2/J3 pins 1-2 vs 3-4) or Vref too low");
  return ok ? R_PASS : R_FAIL;
}

// ---------------------------------------------------------------- menu
void printSummary() {
  Serial.println("\n==== SBR3 hardware test summary ====");
  for (int i = 1; i <= 9; i++) Serial.printf("  %d %-16s %s\n", i, testNames[i], resultName(results[i]));
}

void printMenu() {
  Serial.println("\n==== SBR3 hardware test ====");
  Serial.println("  1 LED  2 buzzer  3 button  4 battery  5 IMU  6 eyes");
  Serial.println("  7 left motor  8 right motor  9 both motors");
  Serial.println("  a run tests 1-6   s summary   m menu");
}

void runTest(char c) {
  switch (c) {
    case '1': results[1] = testStatusLed(); break;
    case '2': results[2] = testBuzzer(); break;
    case '3': results[3] = testButton(); break;
    case '4': results[4] = testBattery(); break;
    case '5': results[5] = testImu(); break;
    case '6': results[6] = testEyes(); break;
    case '7': results[7] = testMotor(0); break;
    case '8': results[8] = testMotor(1); break;
    case '9': results[9] = testMotor(2); break;
    case 'a':
      for (char t = '1'; t <= '6'; t++) runTest(t);
      printSummary();
      return;
    case 's': printSummary(); return;
    case 'm': printMenu(); return;
    default: return;
  }
  int idx = c - '0';
  Serial.printf("  -> %s: %s\n", testNames[idx], resultName(results[idx]));
}

void setup() {
  // Motors off first: the board pull-up already holds ~ENABLE high, drive it high as well.
  pinMode(PIN_MOT_EN_N, OUTPUT);
  digitalWrite(PIN_MOT_EN_N, HIGH);
  for (int p : {PIN_M1_STEP, PIN_M1_DIR, PIN_M2_STEP, PIN_M2_DIR, PIN_BUZZER, PIN_STATUS_LED}) {
    pinMode(p, OUTPUT);
    digitalWrite(p, LOW);
  }
  for (int p : {PIN_MAX_CS_L, PIN_MAX_CS_R}) {
    pinMode(p, OUTPUT);
    digitalWrite(p, HIGH);
  }
  pinMode(PIN_BUTTON, INPUT);   // external 10k pull-up
  pinMode(PIN_IMU_INT, INPUT);
  analogSetPinAttenuation(PIN_VBAT, ADC_11db);

  Serial.begin(115200);
  uint32_t t0 = millis();
  while (!Serial && millis() - t0 < 3000) delay(10);
  Wire.begin(PIN_SDA, PIN_SCL, 400000);
  SPI.begin(PIN_MAX_CLK, -1, PIN_MAX_DIN, -1);

  Serial.printf("\nSBR3 bring-up | %s rev %d | %d MHz | flash %lu MB | PSRAM %lu kB\n", ESP.getChipModel(),
                ESP.getChipRevision(), ESP.getCpuFreqMHz(), (unsigned long)(ESP.getFlashChipSize() >> 20),
                (unsigned long)(ESP.getPsramSize() >> 10));
  printMenu();
}

void loop() {
  if (Serial.available()) {
    char c = tolower(Serial.read());
    if (c != '\r' && c != '\n') runTest(c);
  }
  // heartbeat on the status LED while idle
  static uint32_t last = 0;
  if (millis() - last > 1000) {
    last = millis();
    digitalWrite(PIN_STATUS_LED, !digitalRead(PIN_STATUS_LED));
  }
}
