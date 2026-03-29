"""
api_routes.py — Tất cả Flask routes cho hệ thống phân loại rác.

Sử dụng Flask Blueprint để tách routes khỏi file chính.
Bao gồm:
  - Video feed (MJPEG stream)
  - Trang admin / user
  - API: counts, reset, active_user, session_status, end_session, users
"""

import cv2
import threading
from datetime import datetime
from flask import Blueprint, Response, jsonify, request, send_from_directory

from config import STATIC_DIR, POINTS_PER_ITEM
import user_manager as um

# ── Blueprint ─────────────────────────────────────────────────────────
bp = Blueprint('api', __name__)

# ── Shared frame cho video stream ─────────────────────────────────────
outputFrame = None
frame_lock  = threading.Lock()


def update_frame(frame):
    """Cập nhật frame mới nhất (gọi từ main loop)."""
    global outputFrame
    with frame_lock:
        outputFrame = frame.copy()


# ─────────────────────────── ROUTES ───────────────────────────────────

@bp.route('/video_feed')
def video_feed():
    def generate():
        while True:
            with frame_lock:
                if outputFrame is None:
                    continue
                _, enc = cv2.imencode(
                    '.jpg', outputFrame, [int(cv2.IMWRITE_JPEG_QUALITY), 70]
                )
            yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                   + bytearray(enc) + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@bp.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


@bp.route('/')
def admin():
    return send_from_directory(STATIC_DIR, 'admin.html')


@bp.route('/user')
def user_page():
    return send_from_directory(STATIC_DIR, 'user.html')


@bp.route('/api/counts')
def api_counts():
    return jsonify(counts=um.counts, active_user=um.active_user_id)


@bp.route('/api/reset', methods=['POST'])
def api_reset():
    um.counts.update({'METAL': 0, 'PLASTIC': 0, 'other': 0})
    return jsonify(ok=True)


@bp.route('/api/active_user', methods=['GET', 'POST'])
def api_active_user():
    if request.method == 'POST':
        uid = (request.json or {}).get('id', '').strip()
        if not uid:
            return jsonify(ok=False, error='ID trống'), 400
        um.active_user_id = uid
        um.session_points[uid] = {'METAL': 0, 'PLASTIC': 0, 'other': 0}
        if uid not in um.users_db:
            um.users_db[uid] = {'total': 0, 'history': []}
        return jsonify(ok=True, status='session_started', id=uid)
    return jsonify(active=um.active_user_id)


@bp.route('/api/session_status')
def api_session_status():
    if not um.active_user_id:
        return jsonify(active=None)
    sp  = um.session_points.get(um.active_user_id, {'METAL': 0, 'PLASTIC': 0, 'other': 0})
    pts = sum(v * POINTS_PER_ITEM.get(k, 0) for k, v in sp.items())
    total = um.users_db.get(um.active_user_id, {}).get('total', 0)
    return jsonify(active=um.active_user_id, breakdown=sp, session_points=pts, total=total)


@bp.route('/api/end_session', methods=['POST'])
def api_end_session():
    uid = (request.json or {}).get('id', '').strip()
    if not uid or uid != um.active_user_id:
        return jsonify(ok=False, error='Không khớp ID phiên hiện tại'), 400
    sp     = um.session_points.pop(uid, {'METAL': 0, 'PLASTIC': 0, 'other': 0})
    earned = sum(v * POINTS_PER_ITEM.get(k, 0) for k, v in sp.items())
    if uid not in um.users_db:
        um.users_db[uid] = {'total': 0, 'history': []}
    um.users_db[uid]['total'] += earned
    um.users_db[uid]['history'].append({
        'time':      datetime.now().strftime('%Y-%m-%d %H:%M'),
        'earned':    earned,
        'breakdown': sp,
    })
    um.active_user_id = None
    um.save_users()
    return jsonify(ok=True, total_earned=earned, new_total=um.users_db[uid]['total'])


@bp.route('/api/users')
def api_users():
    rows = [{'id': k, 'total': v['total'],
             'last': v['history'][-1]['time'] if v.get('history') else '—'}
            for k, v in um.users_db.items()]
    rows.sort(key=lambda x: x['total'], reverse=True)
    return jsonify(users=rows)
