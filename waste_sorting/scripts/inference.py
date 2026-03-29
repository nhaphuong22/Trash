"""
inference.py — File chính: Camera loop + YOLO inference + Motion detection.

Các module đã tách:
  - config.py            → Hằng số, đường dẫn
  - servo_controller.py  → Điều khiển servo PCA9685
  - user_manager.py      → Quản lý user, session, điểm
  - api_routes.py        → Flask API routes
"""

import cv2
import torch
import time
import gc
import collections
import threading
from flask import Flask
from ultralytics import YOLO

from config import (
    MODEL_PATH, IMG_SIZE, CONF_THRESHOLD, STATIC_DIR,
    ROI_X1, ROI_Y1, ROI_X2, ROI_Y2,
    FRAME_SKIP, REQUIRED_FRAMES,
    MOTION_MIN_PIXELS, OTHER_TIMEOUT,
    COLOR_MAP, SERVO_PLASTIC_CH, SERVO_METAL_CH,
)
from servo_controller import init_pca9685, stop_servo, trigger_servo_logic
import user_manager as um
import api_routes


def draw_dashboard(img):
    """Vẽ bảng đếm rác lên góc trái khung hình."""
    overlay = img.copy()
    cv2.rectangle(overlay, (5, 5), (230, 155), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, img, 0.4, 0, img)
    cv2.putText(img, 'WASTE TRACKER', (15, 30),
                cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 2)
    cv2.putText(img, f"METAL:   {um.counts['METAL']}",   (20, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_MAP['METAL'],   2)
    cv2.putText(img, f"PLASTIC: {um.counts['PLASTIC']}", (20, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_MAP['PLASTIC'], 2)
    cv2.putText(img, f"OTHER:   {um.counts['other']}",   (20, 130),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_MAP['OTHER'],   2)
    if um.active_user_id:
        cv2.putText(img, f'USER: {um.active_user_id}', (20, 155),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)


def main():
    um.load_users()
    init_pca9685()

    # ── Khởi động Flask (background thread) ──────────────────────────
    app = Flask(__name__, static_folder=STATIC_DIR)
    app.register_blueprint(api_routes.bp)

    threading.Thread(
        target=lambda: app.run(
            host='0.0.0.0', port=5000, threaded=True, use_reloader=False
        ),
        daemon=True,
    ).start()

    # ── Load YOLO model ──────────────────────────────────────────────
    print('[INFO] LOAD MODEL:', MODEL_PATH)
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print('[ERR] CAMERA FAIL')
        return

    frame_count   = 0
    last_act_time = time.time()
    history       = collections.deque(maxlen=10)

    # Thuật toán trừ nền MOG2
    backSub = cv2.createBackgroundSubtractorMOG2(
        history=500, varThreshold=50, detectShadows=False
    )
    kernel_morph = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

    # Trạng thái theo dõi vật trên băng chuyền
    is_tracking_object          = False
    object_detected_time        = 0
    last_motion_time            = 0
    AI_classified_current_object = False

    print('[INFO] Admin : http://0.0.0.0:5000/')
    print('[INFO] User  : http://0.0.0.0:5000/user')

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            draw_dashboard(frame)
            cv2.rectangle(frame, (ROI_X1, ROI_Y1), (ROI_X2, ROI_Y2), (255, 0, 0), 2)

            if frame_count % FRAME_SKIP == 0:
                roi = frame[ROI_Y1:ROI_Y2, ROI_X1:ROI_X2]

                # --- Phát hiện chuyển động (Background Subtraction) ---
                fgMask = backSub.apply(roi)
                _, fgMask = cv2.threshold(fgMask, 200, 255, cv2.THRESH_BINARY)
                fgMask = cv2.morphologyEx(fgMask, cv2.MORPH_OPEN, kernel_morph)
                motion_pixels = cv2.countNonZero(fgMask)

                cv2.putText(frame, f"Motion: {motion_pixels}", (ROI_X1, ROI_Y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                # Có vật tiến vào?
                if motion_pixels > MOTION_MIN_PIXELS:
                    last_motion_time = time.time()
                    if not is_tracking_object:
                        is_tracking_object = True
                        object_detected_time = time.time()
                        AI_classified_current_object = False
                        print("[MOTION] >>> Có vật thể tiến vào băng chuyền...")

                # --- YOLO predict ---
                results = model.predict(
                    source=roi, conf=CONF_THRESHOLD, imgsz=IMG_SIZE,
                    device=0, verbose=False,
                )[0]

                best_det, max_area = None, 0
                for box in results.boxes:
                    bx1, by1, bx2, by2 = map(int, box.xyxy[0])
                    area = (bx2 - bx1) * (by2 - by1)
                    if area > 1500 and area > max_area:
                        max_area = area
                        best_det = {
                            'box':   (bx1+ROI_X1, by1+ROI_Y1, bx2+ROI_X1, by2+ROI_Y1),
                            'label': model.names[int(box.cls[0])].upper(),
                        }

                if best_det:
                    history.append(best_det['label'])
                    cv2.rectangle(
                        frame,
                        (best_det['box'][0], best_det['box'][1]),
                        (best_det['box'][2], best_det['box'][3]),
                        COLOR_MAP.get(best_det['label'], (255, 255, 255)), 2,
                    )
                else:
                    history.append(None)

            # ── Chốt nhãn METAL / PLASTIC khi đủ frame ổn định ──────
            valid_hits = [h for h in history if h in ['METAL', 'PLASTIC']]

            if len(valid_hits) >= REQUIRED_FRAMES:
                stable_cls = collections.Counter(valid_hits).most_common(1)[0][0]

                if (time.time() - last_act_time) > 6:
                    threading.Thread(
                        target=lambda cls=stable_cls: (
                            time.sleep(5),
                            trigger_servo_logic(
                                cls, um.counts, um.active_user_id, um.session_points
                            ),
                        ),
                        daemon=True,
                    ).start()

                    last_act_time = time.time()
                    history.clear()
                    AI_classified_current_object = True

            # ── Xử lý logic 'OTHER' dựa trên chuyển động ────────────
            if is_tracking_object and (time.time() - last_motion_time) > 1.5:
                if not AI_classified_current_object:
                    print("[OTHER] Vật đi qua mà AI không nhận diện được -> Cộng OTHER.")
                    trigger_servo_logic('other', um.counts, um.active_user_id, um.session_points)
                is_tracking_object = False
                print("[MOTION] <<< Đã xử lý xong vật.")

            if is_tracking_object and not AI_classified_current_object:
                if (time.time() - object_detected_time) > OTHER_TIMEOUT:
                    print("[OTHER] Thời gian ngâm trong camera quá lâu -> Cộng OTHER.")
                    trigger_servo_logic('other', um.counts, um.active_user_id, um.session_points)
                    AI_classified_current_object = True

            # Cập nhật frame cho video stream
            api_routes.update_frame(frame)

            if frame_count % 100 == 0:
                torch.cuda.empty_cache()
                gc.collect()

    except KeyboardInterrupt:
        print('[INFO] STOP')
    finally:
        from servo_controller import pca
        if pca:
            for ch in [SERVO_PLASTIC_CH, SERVO_METAL_CH]:
                stop_servo(ch)
        cap.release()
        print('[INFO] CLEANUP DONE')


if __name__ == '__main__':
    main()
