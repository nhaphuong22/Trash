"""
user_manager.py — Quản lý dữ liệu người dùng và session.

Bao gồm:
  - Global state: counts, active_user_id, session_points, users_db
  - load_users / save_users (đọc/ghi users_data.json)
"""

import os
import json
import threading

from config import DATA_FILE

# ── Global State (dùng chung giữa API routes và main loop) ──────────
counts         = {'METAL': 0, 'PLASTIC': 0, 'other': 0}
active_user_id = None
session_points = {}
users_db       = {}
data_lock      = threading.Lock()


def load_users():
    """Đọc users_data.json vào users_db."""
    global users_db
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                users_db = json.load(f)
        except Exception:
            users_db = {}


def save_users():
    """Ghi users_db ra file JSON (thread-safe)."""
    with data_lock:
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(users_db, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print('[ERR] save_users:', e)
