# ============================================================
#  attendance.py  –  Real-time face recognition + auto attendance
#
#  Flow:
#   1. Load master face encodings from .pkl
#   2. Open webcam
#   3. For every frame: detect → recognise → mark DB if new
#   4. Live overlay shows name, status, time, count
#   5. Press 'q' to stop; CSV auto-exported on exit
# ============================================================

import os
import cv2
import face_recognition
import pickle
import time
import csv
import numpy as np
from datetime import datetime, date

from config import (
    ENCODINGS_FILE, REPORTS_DIR,
    TOLERANCE, MODEL, FRAME_RESIZE, CAMERA_INDEX,
    COOLDOWN_SECONDS, UNKNOWN_LABEL,
    COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_WHITE, COLOR_BLACK, COLOR_BLUE
)
from db import mark_attendance, get_student, get_attendance_by_date

# ------------------------------------------------------------------
# Load encodings
# ------------------------------------------------------------------

def load_encodings() -> dict | None:
    if not os.path.exists(ENCODINGS_FILE):
        print(f"[ERROR] Encodings file not found: {ENCODINGS_FILE}")
        print("[INFO]  Run register_face.py first to register students.")
        return None
    with open(ENCODINGS_FILE, "rb") as f:
        data = pickle.load(f)
    print(f"[INFO] Loaded encodings for {len(data['student_ids'])} students.")
    return data


# ------------------------------------------------------------------
# Draw UI overlay on frame
# ------------------------------------------------------------------

def draw_overlay(frame, name: str, student_id: str, status: str,
                 top: int, right: int, bottom: int, left: int):
    """Draw bounding box + label on the frame."""
    if name == UNKNOWN_LABEL:
        box_color  = COLOR_RED
        label_text = "Unknown"
    elif status == "already":
        box_color  = COLOR_YELLOW
        label_text = f"{name} | Already Marked"
    else:
        box_color  = COLOR_GREEN
        label_text = f"{name} | {status.upper()}"

    # Bounding box
    cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)

    # Label background
    label_y = bottom + 25
    cv2.rectangle(frame, (left, bottom), (right, label_y), box_color, cv2.FILLED)
    cv2.putText(frame, label_text, (left + 4, label_y - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, COLOR_WHITE, 1)


def draw_info_bar(frame, subject: str, marked_count: int, total: int):
    """Top status bar with subject, time, count."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, 0), (w, 45), COLOR_BLACK, -1)
    now_str = datetime.now().strftime("%d-%b-%Y  %H:%M:%S")
    text    = (f"Subject: {subject}   |   "
               f"Marked: {marked_count}   |   "
               f"Registered: {total}   |   "
               f"{now_str}")
    cv2.putText(frame, text, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_WHITE, 1)


def draw_instructions(frame):
    """Bottom hint bar."""
    h, w = frame.shape[:2]
    cv2.rectangle(frame, (0, h - 30), (w, h), COLOR_BLACK, -1)
    cv2.putText(frame, "Press 'q' to quit and export attendance CSV",
                (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLOR_WHITE, 1)


# ------------------------------------------------------------------
# CSV export
# ------------------------------------------------------------------

def export_csv(subject: str):
    """Export today's attendance to a timestamped CSV in /reports."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    records = get_attendance_by_date(date.today(), subject)

    if not records:
        print("[INFO] No records to export.")
        return

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_subj  = subject.replace(" ", "_").replace("/", "-")
    filename   = f"attendance_{safe_subj}_{timestamp}.csv"
    filepath   = os.path.join(REPORTS_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)

    print(f"\n[INFO] CSV exported → {filepath}")
    return filepath


# ------------------------------------------------------------------
# Core recognition loop
# ------------------------------------------------------------------

def run_attendance(subject: str = "General", class_start_str: str | None = None):
    """
    Main attendance loop.

    Args:
        subject           : subject name for this session
        class_start_str   : optional "HH:MM" string for late detection
    """
    # Parse class start time
    class_start = None
    if class_start_str:
        try:
            class_start = datetime.strptime(class_start_str, "%H:%M").time()
        except ValueError:
            print("[WARN] Invalid class start time format. Using None.")

    # Load encodings
    data = load_encodings()
    if data is None:
        return

    known_encodings = data["encodings"]
    known_ids       = data["student_ids"]
    known_names     = data["names"]

    # Open camera
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera. Check CAMERA_INDEX in config.py")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS,          30)

    print(f"\n[INFO] Attendance session started | Subject: {subject}")
    print("[INFO] Press 'q' to stop.\n")

    # State tracking
    marked_today:   set  = set()   # student_ids marked in this session
    cooldown_map:   dict = {}      # student_id → last_mark_timestamp
    face_labels:    dict = {}      # track last label per face for smooth display
    process_this    = True         # alternate frames for speed

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        if process_this:
            # Resize for faster processing
            small_frame = cv2.resize(frame, (0, 0),
                                     fx=FRAME_RESIZE, fy=FRAME_RESIZE)
            rgb_small   = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

            # Detect & encode faces
            face_locs  = face_recognition.face_locations(rgb_small, model="hog")
            face_encs  = face_recognition.face_encodings(rgb_small, face_locs)

            face_labels = {}

            for enc, loc in zip(face_encs, face_locs):
                top, right, bottom, left = [int(v / FRAME_RESIZE) for v in loc]

                # Compare against known encodings
                distances = face_recognition.face_distance(known_encodings, enc)

                name       = UNKNOWN_LABEL
                student_id = ""
                status     = "unknown"

                if len(distances) > 0:
                    best_idx = int(np.argmin(distances))
                    if distances[best_idx] <= TOLERANCE:
                        student_id = known_ids[best_idx]
                        name       = known_names[best_idx]

                        # Cooldown check
                        now       = time.time()
                        last_mark = cooldown_map.get(student_id, 0)

                        if (now - last_mark) >= COOLDOWN_SECONDS:
                            # Get full info from DB
                            student = get_student(student_id)
                            dept    = student["department"] if student else "Unknown"

                            result = mark_attendance(
                                student_id, name, dept,
                                subject, class_start
                            )
                            cooldown_map[student_id] = now

                            if result == "marked":
                                marked_today.add(student_id)
                                status = "marked"
                                print(f"  ✅  {name} ({student_id}) – ATTENDANCE MARKED")
                            elif result == "already":
                                marked_today.add(student_id)
                                status = "already"
                            else:
                                status = "error"
                        else:
                            status = "already"
                            marked_today.add(student_id)

                face_labels[(top, right, bottom, left)] = (name, student_id, status)

        process_this = not process_this  # alternate frame processing

        # ------ Draw UI ------
        for (top, right, bottom, left), (name, sid, status) in face_labels.items():
            draw_overlay(frame, name, sid, status, top, right, bottom, left)

        draw_info_bar(frame, subject, len(marked_today), len(known_ids))
        draw_instructions(frame)

        cv2.imshow("Face Attendance System – Press Q to quit", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    print(f"\n[INFO] Session ended. Total marked: {len(marked_today)}")
    export_csv(subject)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "="*50)
    print("   FACE RECOGNITION ATTENDANCE SYSTEM")
    print("="*50)

    subjects_list = [
        "General", "CS301-Data Structures", "CS302-Operating Systems",
        "CS303-Database Management", "CS401-Machine Learning", "CS402-Computer Networks"
    ]

    print("\nAvailable Subjects:")
    for i, s in enumerate(subjects_list, 1):
        print(f"  {i}. {s}")
    print(f"  {len(subjects_list)+1}. Enter custom subject")

    choice = input("\nSelect subject number: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(subjects_list):
            subject = subjects_list[idx]
        else:
            subject = input("Enter subject name: ").strip() or "General"
    except ValueError:
        subject = "General"

    class_start = input("Class start time (HH:MM) or press Enter to skip: ").strip()

    run_attendance(subject, class_start if class_start else None)
