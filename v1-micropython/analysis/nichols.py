import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# 1. LOAD AND CLEAN THE TELEPLOT EXPORT
file_path = 'teleplot_2026-5-23_13-39.csv'

# Teleplot adds a trailing comma on each line, which creates an empty column
df = pd.read_csv(file_path, sep=',', engine='python', on_bad_lines='skip')
df = df.dropna(axis=1, how='all')
cols = df.columns

# Values use a decimal comma, e.g. "1779518323,333"
def parse_vietnamese_float(val):
    if isinstance(val, str):
        clean_str = val.replace('"', '').replace(',', '.')
        try:
            return float(clean_str)
        except ValueError:
            return np.nan
    return val

time_col, angle_col = cols[0], cols[1]
df[time_col] = df[time_col].apply(parse_vietnamese_float)
df[angle_col] = df[angle_col].apply(parse_vietnamese_float)
df = df.dropna()

# Start the time axis at 0
df[time_col] = df[time_col] - df[time_col].iloc[0]

time = df[time_col].values
angle = df[angle_col].values

# 2. ULTIMATE PERIOD Tu
# `distance` (min samples between peaks) and `prominence` filter out small noise peaks
peaks, _ = find_peaks(angle, distance=10, prominence=0.5)

peak_times = time[peaks]
periods = np.diff(peak_times)
Tu = np.mean(periods)

print(f"Ultimate period Tu: {Tu:.4f} s")

# 3. ZIEGLER-NICHOLS PID GAINS
Ku = 120  # gain at which the robot oscillated steadily

Kp_zn = 0.6 * Ku
Ki_zn = 1.2 * Ku / Tu
Kd_zn = 0.075 * Ku * Tu

print("\n--- Ziegler-Nichols PID gains (parallel form) ---")
print(f"Kp = {Kp_zn:.4f}")
print(f"Ki = {Ki_zn:.4f}")
print(f"Kd = {Kd_zn:.4f}")

# 4. PLOT
plt.figure(figsize=(12, 6))
plt.plot(time, angle, label='Tilt angle', color='#1f77b4', linewidth=1.5)
plt.plot(time[peaks], angle[peaks], "x", color='red', markersize=10, markeredgewidth=2, label='Peaks')

plt.title(f"Sustained oscillation at Kp = Ku\nMean period Tu = {Tu:.4f} s", fontsize=14, fontweight='bold')
plt.xlabel('Time (s)', fontsize=12)
plt.ylabel('Tilt angle (deg)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=12)
plt.tight_layout()

plt.savefig('../../docs/oscillation_plot.png', dpi=300)
plt.show()
