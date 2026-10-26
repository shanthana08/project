# ============================================================
#  config.py  –  Central configuration for the entire project
# ============================================================

import os

# ------------------------------------------------------------------
# MySQL connection settings  (edit these to match your setup)
# ------------------------------------------------------------------
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",          # your MySQL username
    "password": "yourpassword",  # your MySQL password
    "database": "face_attendance_db",
    "charset":  "utf8mb4",
}

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR    = os.path.join(BASE_DIR, "dataset")    # student photo folders
ENCODINGS_DIR  = os.path.join(BASE_DIR, "encodings")  # .pkl encoding files
REPORTS_DIR    = os.path.join(BASE_DIR, "reports")    # exported CSV files
ENCODINGS_FILE = os.path.join(ENCODINGS_DIR, "encodings.pkl")  # master encoding

# ------------------------------------------------------------------
# Face-recognition tuning
# ------------------------------------------------------------------
TOLERANCE       = 0.5      # lower = stricter match (0.4–0.6 is ideal)
MODEL           = "hog"    # "hog" (CPU-fast) or "cnn" (GPU-accurate)
FRAME_RESIZE    = 0.5      # scale down frame for faster processing
UNKNOWN_LABEL   = "Unknown"

# ------------------------------------------------------------------
# Attendance rules
# ------------------------------------------------------------------
LATE_THRESHOLD_MINUTES = 15   # if student arrives >15 min late → "Late"
COOLDOWN_SECONDS       = 30   # min seconds before re-marking same student

# ------------------------------------------------------------------
# Camera
# ------------------------------------------------------------------
CAMERA_INDEX = 0   # 0 = default webcam; change if using USB/IP cam

# ------------------------------------------------------------------
# UI colours (BGR format for OpenCV)
# ------------------------------------------------------------------
COLOR_GREEN  = (0, 255, 0)
COLOR_RED    = (0, 0, 255)
COLOR_YELLOW = (0, 255, 255)
COLOR_WHITE  = (255, 255, 255)
COLOR_BLACK  = (0, 0, 0)
COLOR_BLUE   = (255, 0, 0)
