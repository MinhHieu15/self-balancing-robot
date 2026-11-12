# Self-Balancing Robot (ESP32 + MPU6050)

Robot hai bánh tự cân bằng: thiết kế mạch PCB, mô hình 3D khung robot, firmware MicroPython trên ESP32 và các bộ điều khiển **PID** (chạy trên robot thật) và **LQR** (mô phỏng, so sánh với PID).

![Dao động tới hạn](docs/oscillation_plot.png)

## Phần cứng
| Thành phần | Chi tiết |
|---|---|
| Vi điều khiển | ESP32 (MicroPython) |
| Cảm biến | MPU6050 (I2C 400 kHz, SDA=22, SCL=23) |
| Driver động cơ | Cầu H 2 kênh (PWM 2 kHz; kênh A: 25/27/26, kênh B: 13/14/12) |
| PCB | Thiết kế trên KiCad (`hardware/pcb/`) |
| Khung | Mô hình 3D in FDM (`hardware/3d-model/`) |

## Cấu trúc
```
firmware/main.py           # Firmware ESP32: đọc MPU6050, lọc bù, PID, phát hiện ngã
analysis/nichols.py        # Tìm chu kỳ dao động tới hạn Tu từ dữ liệu Teleplot -> PID Ziegler–Nichols
analysis/data_compare_angle.py  # Vẽ đáp ứng góc so với setpoint
analysis/*.csv, *.xlsx     # Dữ liệu góc đo được trên robot
simulation/pid_vs_lqr.py   # Mô phỏng cart-pole: so sánh PID và LQR
hardware/                  # File PCB (KiCad) và 3D (STL/STEP)
docs/                      # Hình kết quả
```

## Thuật toán
**Ước lượng góc:** bộ lọc bù (complementary filter) kết hợp gia tốc kế và con quay hồi chuyển:

$$\theta_k = \alpha(\theta_{k-1} + \omega\,\Delta t) + (1-\alpha)\,\theta_{acc}, \quad \alpha = 0.98$$

**PID (robot thật):** điều khiển góc nghiêng quanh điểm cân bằng, có dead-band ±0.2°, chống bão hòa tích phân (giới hạn I-term), tự ngắt động cơ khi nghiêng quá 45° hoặc mất kết nối I2C.
Thông số được chỉnh bằng phương pháp **Ziegler–Nichols**: tăng Kp tới khi dao động duy trì (Ku = 120), đo chu kỳ Tu từ dữ liệu (`analysis/nichols.py`), rồi tinh chỉnh tay → Kp = 120, Ki = 550, Kd = 0.2.

**LQR (mô phỏng):** tuyến tính hóa mô hình con lắc ngược trên xe quanh vị trí thẳng đứng, giải phương trình Riccati để có `u = -Kx`. Khác với PID chỉ điều khiển góc, LQR điều khiển cả vị trí và vận tốc nên robot không bị trôi.

![PID vs LQR](docs/pid_vs_lqr.png)

Với cùng góc nghiêng ban đầu 10°, cả hai bộ điều khiển đều giữ được thăng bằng, nhưng PID làm robot trôi dần khỏi vị trí ban đầu, còn LQR đưa robot quay về vị trí 0.

## Chạy
```bash
# Firmware: nạp firmware/main.py lên ESP32 (Thonny hoặc mpremote)
mpremote cp firmware/main.py :main.py

# Phân tích / mô phỏng
pip install numpy scipy matplotlib pandas
cd analysis && python nichols.py
cd ../simulation && python pid_vs_lqr.py
```

## Hướng phát triển
- Đưa LQR lên firmware (cần thêm encoder để đo vận tốc bánh).
- Thử MPC và so sánh với LQR.
