"""
config.py — Tất cả hằng số và cấu hình cho hệ thống phân loại rác.

Khi cần thay đổi ngưỡng, đường dẫn, hoặc thông số phần cứng
→ chỉ cần sửa file duy nhất này.
"""

import os
import torch

# ── Tối ưu PyTorch ──────────────────────────────────────────────────
torch.backends.cudnn.benchmark = True
os.environ['OPENBLAS_CORETYPE'] = 'ARMV8'
os.environ['LD_PRELOAD'] = '/usr/lib/aarch64-linux-gnu/libgomp.so.1'

# ── Đường dẫn ────────────────────────────────────────────────────────
THIS_DIR   = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(THIS_DIR, '..', 'static')
DATA_FILE  = os.path.join(THIS_DIR, '..', 'users_data.json')

MODEL_PATH = os.path.join(THIS_DIR, '..', 'models', 'waste_sorter', 'weights', 'best.engine')
if not os.path.exists(MODEL_PATH):
    MODEL_PATH = os.path.join(THIS_DIR, '..', 'models', 'waste_sorter', 'weights', 'best.pt')

# ── YOLO / Camera ────────────────────────────────────────────────────
IMG_SIZE       = 320
CONF_THRESHOLD = 0.50
ROI_X1, ROI_Y1, ROI_X2, ROI_Y2 = 150, 100, 490, 380
FRAME_SKIP      = 2
REQUIRED_FRAMES = 3

# ── Motion detection ─────────────────────────────────────────────────
MOTION_MIN_PIXELS = 3000   # Ngưỡng pixel để phát hiện có vật đi vào camera
OTHER_TIMEOUT     = 6.0    # Quá 6 giây mà AI không dán nhãn Metal/Plastic thì chốt 'Other'

# ── Servo (PCA9685) ──────────────────────────────────────────────────
SERVO_PLASTIC_CH = 0   # CH0
SERVO_METAL_CH   = 1   # CH1

# ── Điểm thưởng ──────────────────────────────────────────────────────
POINTS_PER_ITEM = {'METAL': 10, 'PLASTIC': 5, 'other': 1}

# ── Màu hiển thị (BGR) — khớp chữ IN HOA của YOLO ────────────────────
COLOR_MAP = {
    'METAL':   (0, 255, 0),
    'PLASTIC': (0, 0, 255),
    'OTHER':   (128, 128, 128),
}
