# Self-Balancing Robot (ESP32 + MPU6050)

Two-wheeled self-balancing robot with a custom PCB, a 3D-printed frame and MicroPython firmware on an ESP32. A PID controller runs on the robot; an LQR controller is compared against it in simulation.

![Sustained oscillation used for Ziegler-Nichols tuning](docs/oscillation_plot.png)

## Hardware
| Part | Details |
|---|---|
| MCU | ESP32, MicroPython |
| IMU | MPU6050, I2C 400 kHz (SDA 22, SCL 23) |
| Motor driver | Dual H-bridge, 2 kHz PWM (A: 25/27/26, B: 13/14/12) |
| PCB | KiCad, `hardware/pcb/` |
| Frame | 3D model, `hardware/3d-model/` |

## Layout
```
firmware/main.py                # MPU6050, complementary filter, PID, fall detection
analysis/nichols.py             # ultimate period Tu from Teleplot data, Ziegler-Nichols gains
analysis/data_compare_angle.py  # ITAE of the measured angle per 1 s window
analysis/*.csv, *.xlsx          # tilt angle logged on the robot
simulation/pid_vs_lqr.py        # cart-pole simulation, PID vs LQR
hardware/                       # PCB and 3D files
docs/                           # plots
```

## Tilt estimate
Complementary filter on the accelerometer angle and the integrated gyro rate:

$$\theta_k = \alpha(\theta_{k-1} + \omega\,\Delta t) + (1-\alpha)\,\theta_{acc}, \quad \alpha = 0.98$$

## PID
The controller works on the tilt error around the balance point, with a ±0.2° dead band and a clamped integral term. The motors stop when the tilt goes past 45° or an I2C read fails, and start again once the robot is upright.

Tuning started from Ziegler-Nichols: Kp was raised until the robot oscillated steadily (Ku = 120), `analysis/nichols.py` measured the period Tu from the log, and the gains were then adjusted by hand to Kp = 120, Ki = 550, Kd = 0.2.

## LQR (simulation)
The cart-pole model is linearised about upright and the Riccati equation gives `u = -Kx`. Since LQR uses position and velocity as well as the angle, the robot doesn't drift the way it does with PID.

![PID vs LQR](docs/pid_vs_lqr.png)

From a 10° initial tilt both controllers keep the robot up. With PID it drifts about 7 cm and keeps going; with LQR it comes back to where it started.

## Running the analysis
```bash
pip install numpy scipy matplotlib pandas
cd analysis && python nichols.py
cd ../simulation && python pid_vs_lqr.py
```
