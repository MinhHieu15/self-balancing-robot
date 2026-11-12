"""
So sánh bộ điều khiển PID và LQR trên mô hình con lắc ngược trên xe (cart-pole),
mô hình rút gọn của robot tự cân bằng hai bánh.

Trạng thái: x = [vị trí xe, vận tốc xe, góc nghiêng theta, vận tốc góc]
Đầu vào:    F  = lực đẩy tại bánh xe (N)

- PID chỉ điều khiển góc theta  -> robot đứng được nhưng trôi vị trí.
- LQR điều khiển toàn bộ trạng thái -> giữ thăng bằng và quay về vị trí ban đầu.

Chạy:  python pid_vs_lqr.py   (lưu hình ra ../docs/pid_vs_lqr.png)
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import solve_continuous_are

# ================= THAM SỐ MÔ HÌNH =================
M = 0.5    # khối lượng phần bánh/đế (kg)
m = 0.8    # khối lượng thân robot (kg)
l = 0.10   # khoảng cách từ trục bánh tới trọng tâm thân (m)
g = 9.81
F_MAX = 20.0  # giới hạn lực (bão hòa động cơ)

THETA0 = np.deg2rad(10)  # góc nghiêng ban đầu
T_END = 5.0


def dynamics(state, F):
    """Phương trình phi tuyến của cart-pole (theta = 0 là thẳng đứng)."""
    _, x_dot, th, th_dot = state
    s, c = np.sin(th), np.cos(th)
    den = M + m * s**2
    x_dd = (F + m * l * th_dot**2 * s - m * g * s * c) / den
    th_dd = (-F * c - m * l * th_dot**2 * s * c + (M + m) * g * s) / (l * den)
    return np.array([x_dot, x_dd, th_dot, th_dd])


# ================= LQR =================
A = np.array([
    [0, 1, 0, 0],
    [0, 0, -m * g / M, 0],
    [0, 0, 0, 1],
    [0, 0, (M + m) * g / (M * l), 0],
])
B = np.array([[0], [1 / M], [0], [-1 / (M * l)]])
Q = np.diag([10, 1, 100, 1])  # phạt sai lệch vị trí và góc
R = np.array([[0.1]])

P = solve_continuous_are(A, B, Q, R)
K = np.linalg.inv(R) @ B.T @ P  # u = -K x


def lqr_rhs(t, s):
    F = float(np.clip(-(K @ s)[0], -F_MAX, F_MAX))
    return dynamics(s, F)


# ================= PID (chỉ trên góc) =================
Kp, Ki, Kd = 30.0, 50.0, 1.0


def pid_rhs(t, s):
    state, integ = s[:4], s[4]
    th, th_dot = state[2], state[3]
    F = float(np.clip(Kp * th + Ki * integ + Kd * th_dot, -F_MAX, F_MAX))
    return np.append(dynamics(state, F), th)


def main():
    t_eval = np.linspace(0, T_END, 1000)
    x0 = np.array([0, 0, THETA0, 0])

    lqr = solve_ivp(lqr_rhs, (0, T_END), x0, t_eval=t_eval, max_step=1e-3)
    pid = solve_ivp(pid_rhs, (0, T_END), np.append(x0, 0), t_eval=t_eval, max_step=1e-3)

    print("Ma trận K của LQR:", np.round(K, 3))
    print(f"Góc cuối  - PID: {np.rad2deg(pid.y[2, -1]):+.3f} deg | LQR: {np.rad2deg(lqr.y[2, -1]):+.3f} deg")
    print(f"Vị trí cuối - PID: {pid.y[0, -1]:+.3f} m   | LQR: {lqr.y[0, -1]:+.3f} m")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ax1.plot(pid.t, np.rad2deg(pid.y[2]), label="PID")
    ax1.plot(lqr.t, np.rad2deg(lqr.y[2]), label="LQR")
    ax1.set_ylabel("Góc nghiêng (deg)")
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend()
    ax2.plot(pid.t, pid.y[0], label="PID")
    ax2.plot(lqr.t, lqr.y[0], label="LQR")
    ax2.set_ylabel("Vị trí (m)")
    ax2.set_xlabel("Thời gian (s)")
    ax2.grid(True, linestyle="--", alpha=0.6)
    fig.suptitle(f"Robot tự cân bằng: PID vs LQR (góc ban đầu {np.rad2deg(THETA0):.0f}°)")
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), "..", "docs", "pid_vs_lqr.png")
    fig.savefig(out, dpi=150)
    print("Đã lưu", os.path.normpath(out))
    plt.show()


if __name__ == "__main__":
    main()
