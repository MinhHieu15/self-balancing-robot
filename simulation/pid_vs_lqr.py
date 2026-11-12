"""
PID vs LQR on a cart-pole, the simplified model of a two-wheeled self-balancing robot.

State x = [cart position, cart velocity, tilt angle, angular velocity], input F = wheel force (N).
PID only looks at the tilt angle, so the robot balances but drifts. LQR uses the full state
and also brings the robot back to where it started.

Run: python pid_vs_lqr.py   (saves ../docs/pid_vs_lqr.png)
"""
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy.integrate import solve_ivp
from scipy.linalg import solve_continuous_are

M = 0.5    # wheels and base (kg)
m = 0.8    # body (kg)
l = 0.10   # axle to body centre of mass (m)
g = 9.81
F_MAX = 20.0  # motor saturation (N)

THETA0 = np.deg2rad(10)
T_END = 5.0


def dynamics(state, F):
    """Nonlinear cart-pole, theta = 0 is upright."""
    _, x_dot, th, th_dot = state
    s, c = np.sin(th), np.cos(th)
    den = M + m * s**2
    x_dd = (F + m * l * th_dot**2 * s - m * g * s * c) / den
    th_dd = (-F * c - m * l * th_dot**2 * s * c + (M + m) * g * s) / (l * den)
    return np.array([x_dot, x_dd, th_dot, th_dd])


# Linearised about the upright position
A = np.array([
    [0, 1, 0, 0],
    [0, 0, -m * g / M, 0],
    [0, 0, 0, 1],
    [0, 0, (M + m) * g / (M * l), 0],
])
B = np.array([[0], [1 / M], [0], [-1 / (M * l)]])
Q = np.diag([10, 1, 100, 1])
R = np.array([[0.1]])

P = solve_continuous_are(A, B, Q, R)
K = np.linalg.inv(R) @ B.T @ P


def lqr_rhs(t, s):
    F = float(np.clip(-(K @ s)[0], -F_MAX, F_MAX))
    return dynamics(s, F)


Kp, Ki, Kd = 30.0, 50.0, 1.0


def pid_rhs(t, s):
    # s[4] is the integral of the tilt angle
    state, integ = s[:4], s[4]
    th, th_dot = state[2], state[3]
    F = float(np.clip(Kp * th + Ki * integ + Kd * th_dot, -F_MAX, F_MAX))
    return np.append(dynamics(state, F), th)


def main():
    t_eval = np.linspace(0, T_END, 1000)
    x0 = np.array([0, 0, THETA0, 0])

    lqr = solve_ivp(lqr_rhs, (0, T_END), x0, t_eval=t_eval, max_step=1e-3)
    pid = solve_ivp(pid_rhs, (0, T_END), np.append(x0, 0), t_eval=t_eval, max_step=1e-3)

    print("LQR gain K:", np.round(K, 3))
    print(f"Final angle    PID: {np.rad2deg(pid.y[2, -1]):+.3f} deg | LQR: {np.rad2deg(lqr.y[2, -1]):+.3f} deg")
    print(f"Final position PID: {pid.y[0, -1]:+.3f} m   | LQR: {lqr.y[0, -1]:+.3f} m")

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    ax1.plot(pid.t, np.rad2deg(pid.y[2]), label="PID")
    ax1.plot(lqr.t, np.rad2deg(lqr.y[2]), label="LQR")
    ax1.set_ylabel("Tilt angle (deg)")
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.legend()
    ax2.plot(pid.t, pid.y[0], label="PID")
    ax2.plot(lqr.t, lqr.y[0], label="LQR")
    ax2.set_ylabel("Position (m)")
    ax2.set_xlabel("Time (s)")
    ax2.grid(True, linestyle="--", alpha=0.6)
    fig.suptitle(f"Self-balancing robot: PID vs LQR (initial tilt {np.rad2deg(THETA0):.0f}°)")
    fig.tight_layout()

    out = os.path.join(os.path.dirname(__file__), "..", "docs", "pid_vs_lqr.png")
    fig.savefig(out, dpi=150)
    plt.show()


if __name__ == "__main__":
    main()
