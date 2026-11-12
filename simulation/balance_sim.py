"""
Discrete-time simulation of the SBR3 balancing loop at 200 Hz.

Stepper motors set wheel acceleration directly, so the plant is a wheeled inverted pendulum
with wheel acceleration `a` as the input:

    x_dd     = a
    theta_dd = (g sin(theta) - a cos(theta)) / l

The controller never sees the true angle. It gets a complementary-filter estimate built from a
noisy accelerometer and a gyro with bias, one sample late, and its output is limited by the
stepper's maximum acceleration and speed.

Scenarios (plots go to ../docs, logs to results/):
  1. recovery from a 10 deg initial tilt, PID vs LQR
  2. a push (sudden 60 deg/s angular rate) at t = 2 s
  3. loop delay from 0 to 40 ms (IMU read, filtering, step generation)
  4. complementary filter alpha vs angle estimation error
"""
import csv
import os

import matplotlib.pyplot as plt
import numpy as np
from scipy.linalg import solve_discrete_are

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "..", "docs")
RESULTS = os.path.join(HERE, "results")

G = 9.81
L_NOMINAL = 0.075        # axle to centre of mass (m)
TS = 0.005               # 200 Hz control loop
A_MAX = 6.0              # wheel acceleration limit (m/s^2)
V_MAX = 0.9              # 1/16 microstep, ~3200 steps/rev at 10 kHz step rate -> ~0.9 m/s

ACC_NOISE = np.deg2rad(1.5)    # accelerometer angle noise (1 sigma)
GYRO_NOISE = np.deg2rad(0.6)   # gyro rate noise (1 sigma, rad/s)
GYRO_BIAS = np.deg2rad(0.8)    # uncompensated gyro bias (rad/s)


def linear_model(l):
    A = np.array([[0, 1, 0, 0],
                  [0, 0, 0, 0],
                  [0, 0, 0, 1],
                  [0, 0, G / l, 0]])
    B = np.array([[0], [1], [0], [-1 / l]])
    Ad = np.eye(4) + A * TS + A @ A * TS**2 / 2
    Bd = (np.eye(4) * TS + A * TS**2 / 2) @ B
    return Ad, Bd


def lqr_gain(l=L_NOMINAL, q=(20, 5, 400, 10), r=1.0):
    Ad, Bd = linear_model(l)
    Q, R = np.diag(q), np.array([[r]])
    P = solve_discrete_are(Ad, Bd, Q, R)
    return np.linalg.solve(R + Bd.T @ P @ Bd, Bd.T @ P @ Ad)


class PID:
    """Angle loop plus a slow speed loop that leans the robot to stop it drifting."""

    def __init__(self, kp=55.0, ki=60.0, kd=3.2, k_speed=0.06):
        self.kp, self.ki, self.kd, self.k_speed = kp, ki, kd, k_speed
        self.integral = 0.0

    def __call__(self, est):
        x, v, th, om = est
        target = -self.k_speed * v
        e = th - target
        self.integral = np.clip(self.integral + e * TS, -0.5, 0.5)
        return self.kp * e + self.ki * self.integral + self.kd * om


class LQR:
    def __init__(self, K):
        self.K = K

    def __call__(self, est):
        return float(-(self.K @ est)[0])


def simulate(controller, l=L_NOMINAL, theta0=np.deg2rad(10), t_end=6.0, push_at=None,
             push_rate=np.deg2rad(60), alpha=0.98, delay=1, seed=1):
    rng = np.random.default_rng(seed)
    n = int(t_end / TS)
    x, v, th, om = 0.0, 0.0, theta0, 0.0
    th_est = theta0
    pending = [0.0] * delay
    log = np.zeros((n, 7))  # t, x, v, theta, theta_est, omega, a_cmd
    fallen = False
    for k in range(n):
        t = k * TS
        if push_at is not None and abs(t - push_at) < TS / 2:
            om += push_rate

        acc_angle = th + rng.normal(0, ACC_NOISE)
        gyro = om + GYRO_BIAS + rng.normal(0, GYRO_NOISE)
        th_est = alpha * (th_est + gyro * TS) + (1 - alpha) * acc_angle

        # wheel position/speed come from counting steps, so they are exact
        a_cmd = np.clip(controller(np.array([x, v, th_est, gyro])), -A_MAX, A_MAX)
        pending.append(a_cmd)
        a = pending.pop(0)
        if abs(v + a * TS) > V_MAX:
            a = (np.sign(v) * V_MAX - v) / TS

        # integrate the nonlinear plant with 10 substeps
        h = TS / 10
        for _ in range(10):
            th_dd = (G * np.sin(th) - a * np.cos(th)) / l
            om += th_dd * h
            th += om * h
            v += a * h
            x += v * h
        log[k] = (t, x, v, th, th_est, om, a)
        if abs(th) > np.deg2rad(60):
            fallen = True
            log = log[:k + 1]
            break
    return log, fallen


def itae(log):
    t, th = log[:, 0], log[:, 3]
    return float(np.sum(t * np.abs(th)) * TS)


def save_csv(name, log):
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_s", "x_m", "v_mps", "theta_deg", "theta_est_deg", "omega_dps", "wheel_acc_mps2"])
        for r in log:
            w.writerow([f"{r[0]:.3f}", f"{r[1]:.4f}", f"{r[2]:.4f}", f"{np.rad2deg(r[3]):.3f}",
                        f"{np.rad2deg(r[4]):.3f}", f"{np.rad2deg(r[5]):.2f}", f"{r[6]:.3f}"])


def plot_pair(logs, title, fname):
    fig, axes = plt.subplots(3, 1, figsize=(9, 8), sharex=True)
    for label, log in logs.items():
        t = log[:, 0]
        axes[0].plot(t, np.rad2deg(log[:, 3]), label=label)
        axes[1].plot(t, log[:, 1] * 100, label=label)
        axes[2].plot(t, log[:, 6], label=label)
    axes[0].set_ylabel("Tilt (deg)")
    axes[1].set_ylabel("Position (cm)")
    axes[2].set_ylabel("Wheel acc. (m/s²)")
    axes[2].set_xlabel("Time (s)")
    for ax in axes:
        ax.grid(True, linestyle="--", alpha=0.5)
    axes[0].legend()
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS, fname), dpi=140)
    plt.close(fig)


def main():
    os.makedirs(DOCS, exist_ok=True)
    K = lqr_gain()
    print("LQR K =", np.round(K, 2))
    rows = []

    # 1. initial tilt
    pid_log, _ = simulate(PID())
    lqr_log, _ = simulate(LQR(K))
    save_csv("tilt10_pid.csv", pid_log)
    save_csv("tilt10_lqr.csv", lqr_log)
    plot_pair({"PID": pid_log, "LQR": lqr_log}, "Recovery from 10° initial tilt (200 Hz, IMU noise, 1-sample delay)",
              "sim_tilt_recovery.png")
    for name, log in (("PID", pid_log), ("LQR", lqr_log)):
        settle = log[np.abs(np.rad2deg(log[:, 3])) > 1.0, 0]
        rows.append(("10° tilt", name, itae(log), np.rad2deg(np.abs(log[:, 3])).max(),
                     settle[-1] if len(settle) else 0.0, abs(log[-1, 1]) * 100))

    # 2. push
    pid_log, _ = simulate(PID(), theta0=0.0, push_at=2.0)
    lqr_log, _ = simulate(LQR(K), theta0=0.0, push_at=2.0)
    save_csv("push_pid.csv", pid_log)
    save_csv("push_lqr.csv", lqr_log)
    plot_pair({"PID": pid_log, "LQR": lqr_log}, "Push at t = 2 s (+60°/s angular rate)", "sim_push.png")
    for name, log in (("PID", pid_log), ("LQR", lqr_log)):
        after = log[log[:, 0] >= 2.0]
        settle = after[np.abs(np.rad2deg(after[:, 3])) > 1.0, 0]
        rows.append(("push", name, itae(after), np.rad2deg(np.abs(after[:, 3])).max(),
                     (settle[-1] - 2.0) if len(settle) else 0.0, abs(log[-1, 1]) * 100))

    with open(os.path.join(RESULTS, "metrics.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scenario", "controller", "ITAE", "max_tilt_deg", "settling_time_1deg_s", "final_offset_cm"])
        for r in rows:
            w.writerow([r[0], r[1], f"{r[2]:.4f}", f"{r[3]:.2f}", f"{r[4]:.2f}", f"{r[5]:.2f}"])
    for r in rows:
        print(f"{r[0]:9s} {r[1]:4s} ITAE={r[2]:.4f}  max={r[3]:5.2f} deg  settle={r[4]:.2f} s  offset={r[5]:.2f} cm")

    # 3. loop delay
    delays = list(range(0, 9))
    rob = {"PID": [], "LQR": []}
    for d in delays:
        for name, ctrl in (("PID", PID()), ("LQR", LQR(K))):
            log, fallen = simulate(ctrl, delay=d)
            rob[name].append(np.nan if fallen else itae(log))
    with open(os.path.join(RESULTS, "loop_delay.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["delay_ms", "ITAE_PID", "ITAE_LQR"])
        for d, p, q in zip(delays, rob["PID"], rob["LQR"]):
            w.writerow([d * TS * 1000, f"{p:.4f}", f"{q:.4f}"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ms = [d * TS * 1000 for d in delays]
    ax.plot(ms, rob["PID"], "o-", label="PID")
    ax.plot(ms, rob["LQR"], "s-", label="LQR")
    ax.set_xlabel("Loop delay (ms)")
    ax.set_ylabel("ITAE of tilt (rad·s²)")
    ax.set_title("Effect of loop delay, 10° initial tilt (missing point = robot fell)")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS, "sim_loop_delay.png"), dpi=140)
    plt.close(fig)
    for d, p, q in zip(ms, rob["PID"], rob["LQR"]):
        print(f"delay={d:4.0f} ms  PID={p:.4f}  LQR={q:.4f}")

    # 4. complementary filter alpha
    alphas = [0.90, 0.94, 0.96, 0.98, 0.99, 0.995, 0.998]
    rmse = []
    for al in alphas:
        log, fallen = simulate(LQR(K), alpha=al, theta0=0.0, push_at=2.0)
        rmse.append(np.nan if fallen else np.rad2deg(np.sqrt(np.mean((log[:, 4] - log[:, 3]) ** 2))))
    with open(os.path.join(RESULTS, "filter_alpha.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["alpha", "angle_rmse_deg"])
        for al, e in zip(alphas, rmse):
            w.writerow([al, f"{e:.4f}"])
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.semilogx([1 - a for a in alphas], rmse, "o-")
    ax.set_xlabel("1 − α (weight on accelerometer)")
    ax.set_ylabel("Angle estimate RMSE (deg)")
    ax.set_title("Complementary filter: noise vs gyro-bias drift")
    ax.grid(True, which="both", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(os.path.join(DOCS, "sim_filter_alpha.png"), dpi=140)
    plt.close(fig)
    for al, e in zip(alphas, rmse):
        print(f"alpha={al:<6} rmse={e:.3f} deg")


if __name__ == "__main__":
    main()
