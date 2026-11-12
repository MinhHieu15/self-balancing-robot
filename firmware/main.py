from machine import Pin, PWM, I2C
import time
import math

# ================= MOTOR =================
DIR_B = -1 

pwmA = PWM(Pin(25), freq=2000)
AIN1 = Pin(27, Pin.OUT)
AIN2 = Pin(26, Pin.OUT)

pwmB = PWM(Pin(13), freq=2000)
BIN1 = Pin(14, Pin.OUT)
BIN2 = Pin(12, Pin.OUT)

MIN_PWM = 30
MAX_PWM = 800

def set_motor(speed):
    speed = max(min(speed, MAX_PWM), -MAX_PWM)

    if abs(speed) > 0 and abs(speed) < MIN_PWM:
        speed = MIN_PWM if speed > 0 else -MIN_PWM

    # Motor A
    if speed >= 0:
        AIN1.value(0); AIN2.value(1)
    else:
        AIN1.value(1); AIN2.value(0)

    # Motor B
    speed_b = speed * DIR_B
    if speed_b >= 0:
        BIN1.value(0); BIN2.value(1)
    else:
        BIN1.value(1); BIN2.value(0)

    pwmA.duty(int(abs(speed)))
    pwmB.duty(int(abs(speed_b)))


def stop_motor():
    AIN1.value(0); AIN2.value(0)
    BIN1.value(0); BIN2.value(0)
    pwmA.duty(0)
    pwmB.duty(0)

# ================= MPU6050 =================
i2c = I2C(0, scl=Pin(23), sda=Pin(22), freq=400000)
MPU_ADDR = 0x68

def mpu_init():
    try:
        i2c.writeto_mem(MPU_ADDR, 0x6B, b'\x00')
        time.sleep(0.1)
        i2c.readfrom_mem(MPU_ADDR, 0x75, 1)  # test WHO_AM_I
        return True
    except:
        return False

def read_raw(addr):
    data = i2c.readfrom_mem(MPU_ADDR, addr, 2)
    val = (data[0] << 8) | data[1]
    return val - 65536 if val > 32768 else val

# ================= PID =================
Kp = 120
Ki = 550
Kd = 0.2

target_angle = 6.2
alpha = 0.98

angle = 0
i_term = 0
last_error = 0
last_time = time.ticks_ms()

robot_fallen = False

# ================= INIT MPU =================
while not mpu_init():
    print("MPU lỗi, đang thử lại...")
    time.sleep(1)

print("MPU OK")

# ================= LOOP =================
while True:
    now = time.ticks_ms()
    dt = time.ticks_diff(now, last_time) / 1000.0
    if dt <= 0:
        dt = 0.01
    last_time = now

    # ===== ĐỌC MPU (CÓ BẮT LỖI) =====
    try:
        acc_y = read_raw(0x3D) / 16384.0
        acc_z = read_raw(0x3F) / 16384.0
        acc_angle = math.degrees(math.atan2(acc_y, acc_z))
        gyro_x = read_raw(0x43) / 131.0
    except:
        # ❌ Lỗi I2C → dừng ngay
        print("MPU ERROR")
        stop_motor()
        i_term = 0
        robot_fallen = True
        time.sleep(0.01)
        continue

    # ===== FILTER =====
    angle = alpha * (angle + gyro_x * dt) + (1 - alpha) * acc_angle

    # ===== PHÁT HIỆN NGÃ =====
    if abs(angle - target_angle) > 45:
        robot_fallen = True

    # ===== NẾU ĐANG NGÃ =====
    if robot_fallen:
        stop_motor()
        i_term = 0

        # chỉ reset khi dựng lại
        if abs(angle - target_angle) < 10:
            robot_fallen = False

        time.sleep(0.01)
        continue

    # ===== DEAD BAND GÓC =====
    if abs(angle - target_angle) < 0.2:
        error = 0
    else:
        error = angle - target_angle

    # ===== PID =====
    p_term = Kp * error

    i_term += Ki * error * dt
    i_term = max(min(i_term, 150), -150)

    d_term = Kd * (error - last_error) / dt
    last_error = error

    speed_output = p_term + i_term + d_term

    # giảm giật
    #speed_output *= 0.8

    # giới hạn
    speed_output = max(min(speed_output, MAX_PWM), -MAX_PWM)

    # ===== CHẠY =====
    set_motor(speed_output)
    # ===== PRINT DEBUG CHO PLOTTER =====
    print(angle)
    # ===== PRINT DEBUG CHO PLOTTER =====
    #print(f">Angle:{angle}")

