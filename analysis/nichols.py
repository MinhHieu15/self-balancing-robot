import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks

# 1. TẢI VÀ LÀM SẠCH DỮ LIỆU
file_path = 'teleplot_2026-5-23_13-39.csv'

# Đọc file CSV. File của teleplot đôi khi có dấu phẩy ở cuối dòng tạo ra cột rỗng
df = pd.read_csv(file_path, sep=',', engine='python', on_bad_lines='skip')

# Xóa các cột hoàn toàn rỗng
df = df.dropna(axis=1, how='all')
cols = df.columns

# Hàm chuyển đổi chuỗi có dấu phẩy (vd: "1779518323,333") thành float
def parse_vietnamese_float(val):
    if isinstance(val, str):
        # Loại bỏ dấu ngoặc kép nếu có và thay dấu phẩy thành dấu chấm
        clean_str = val.replace('"', '').replace(',', '.')
        try:
            return float(clean_str)
        except ValueError:
            return np.nan
    return val

# Áp dụng chuyển đổi
time_col, angle_col = cols[0], cols[1]
df[time_col] = df[time_col].apply(parse_vietnamese_float)
df[angle_col] = df[angle_col].apply(parse_vietnamese_float)

# Loại bỏ các hàng có giá trị NaN (nếu có)
df = df.dropna()

# Đưa mốc thời gian về 0 để dễ quan sát (giả định cột time là timestamp dạng giây/ms)
df[time_col] = df[time_col] - df[time_col].iloc[0]

time = df[time_col].values
angle = df[angle_col].values

# 2. TÌM CHU KỲ DAO ĐỘNG (Tu)
# Tìm các đỉnh (peaks). Tham số distance giúp bỏ qua các đỉnh nhiễu nhỏ liên tiếp.
# Bạn có thể cần tinh chỉnh tham số 'distance' (số lượng mẫu tối thiểu giữa 2 đỉnh)
peaks, _ = find_peaks(angle, distance=10, prominence=0.5)

# Tính chu kỳ bằng cách lấy chênh lệch thời gian giữa các đỉnh liên tiếp
peak_times = time[peaks]
periods = np.diff(peak_times)

# Tính chu kỳ trung bình
Tu = np.mean(periods)

print(f"Chu kỳ dao động tới hạn (Tu): {Tu:.4f} giây")

# 3. TÍNH TOÁN THÔNG SỐ PID THEO ZIEGLER-NICHOLS
Ku = 120  # Theo thông tin bạn cung cấp

Kp_zn = 0.6 * Ku
Ki_zn = 1.2 * Ku / Tu
Kd_zn = 0.075 * Ku * Tu

print(f"\n--- Thông số PID theo Ziegler-Nichols (Bộ điều khiển song song) ---")
print(f"Kp = {Kp_zn:.4f}")
print(f"Ki = {Ki_zn:.4f}")
print(f"Kd = {Kd_zn:.4f}")

# 4. VẼ ĐỒ THỊ TRỰC QUAN
plt.figure(figsize=(12, 6))
plt.plot(time, angle, label='Góc Theta', color='#1f77b4', linewidth=1.5)
plt.plot(time[peaks], angle[peaks], "x", color='red', markersize=10, markeredgewidth=2, label='Các đỉnh dao động')

plt.title(f"Dao động tự do của Robot \nChu kỳ trung bình Tu = {Tu:.4f}s", fontsize=14, fontweight='bold')
plt.xlabel('Thời gian (giây)', fontsize=12)
plt.ylabel('Góc Theta', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.7)
plt.legend(fontsize=12)
plt.tight_layout()

# Lưu đồ thị ra file ảnh (tùy chọn) và hiển thị
plt.savefig('oscillation_plot.png', dpi=300)
plt.show()