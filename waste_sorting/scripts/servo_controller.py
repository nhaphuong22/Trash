"""
servo_controller.py — Điều khiển servo PCA9685.

Bao gồm:
  - Khởi tạo board I2C + PCA9685
  - set_angle / stop_servo
  - trigger_servo_logic: kích hoạt servo tương ứng với loại rác + cộng điểm
"""

import time
import threading

from config import SERVO_PLASTIC_CH, SERVO_METAL_CH, POINTS_PER_ITEM

# ── Import thư viện PCA9685 (fallback nếu không cài) ────────────────
try:
    from adafruit_pca9685 import PCA9685
    from board import SCL, SDA
    import busio
    PCA9685_LIB_OK = True
except ImportError:
    PCA9685_LIB_OK = False
    print('[WARN] adafruit_pca9685 chưa cài — servo sẽ không hoạt động')

# ── State ─────────────────────────────────────────────────────────────
pca        = None
servo_lock = threading.Lock()


def init_pca9685():
    """Khởi tạo PCA9685 qua I2C. Gọi 1 lần khi khởi động."""
    global pca
    if not PCA9685_LIB_OK:
        print('[WARN] PCA9685 lib không có — bỏ qua')
        return
    try:
        i2c = busio.I2C(SCL, SDA)
        pca = PCA9685(i2c)
        pca.frequency = 50   # 50Hz chuẩn cho servo SG90/MG90
        print('[INFO] PCA9685 READY')
    except Exception as e:
        print('[ERR] PCA9685 INIT FAIL:', e)
        pca = None


def set_angle(channel, angle):
    """Chuyển góc (0-180°) → duty cycle 16-bit cho PCA9685."""
    if pca is None:
        return
    pulse = int(65535 * ((angle * 11) + 500) / 20000)
    pca.channels[channel].duty_cycle = pulse


def stop_servo(channel):
    """Tắt xung tránh servo rung."""
    if pca is None:
        return
    pca.channels[channel].duty_cycle = 0


def trigger_servo_logic(cls, counts, active_user_id, session_points):
    """
    Kích hoạt servo tương ứng với loại rác và cộng điểm.

    Parameters
    ----------
    cls : str
        Loại rác: 'METAL', 'PLASTIC', hoặc 'other'.
    counts : dict
        Bộ đếm {'METAL': n, 'PLASTIC': n, 'other': n}.
    active_user_id : str | None
        ID user đang chơi session.
    session_points : dict
        Điểm tích lũy theo session {uid: {...}}.
    """
    with servo_lock:
        print('SERVO ACTION:', cls)
        counts[cls] = counts.get(cls, 0) + 1

        if cls == 'PLASTIC':
            print('--> PLASTIC (CH0)')
            set_angle(SERVO_PLASTIC_CH, 120)
            time.sleep(2.3)
            set_angle(SERVO_PLASTIC_CH, 60)
            time.sleep(0.3)
            stop_servo(SERVO_PLASTIC_CH)

        elif cls == 'METAL':
            print('--> METAL (CH1)')
            set_angle(SERVO_METAL_CH, 0)
            time.sleep(2.3)
            set_angle(SERVO_METAL_CH, 60)
            time.sleep(0.3)
            stop_servo(SERVO_METAL_CH)

        # Cộng điểm theo session
        if active_user_id:
            sp = session_points.setdefault(
                active_user_id, {'METAL': 0, 'PLASTIC': 0, 'other': 0}
            )
            sp[cls] = sp.get(cls, 0) + 1
            print(f'[POINTS] +{POINTS_PER_ITEM.get(cls, 0)}đ → {active_user_id}')
