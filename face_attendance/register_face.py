# ============================================================
#  register_face.py  –  Register a new student with face data
#
#  Flow:
#   1. Collect student details (CLI prompt)
#   2. Capture multiple face photos via webcam
#   3. Generate face encodings using face_recognition
#   4. Save encodings to master .pkl file
#   5. Save student record to MySQL
# ============================================================

import os
import cv2
import face_recognition
import pickle
import time
import numpy as np
from datetime import datetime

from config import (
    DATASET_DIR, ENCODINGS_FILE, ENCODINGS_DIR,
    CAMERA_INDEX, MODEL,
    COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_WHITE, COLOR_BLUE
)
from db import add_student, get_student

# Number of face samples to capture per student
SAMPLES_NEEDED = 10


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def load_master_encodings() -> dict:
    """Load existing encodings dict from disk (or return empty)."""
    if os.path.exists(ENCODINGS_FILE):
        with open(ENCODINGS_FILE, "rb") as f:
            data = pickle.load(f)
        return data  # {"student_ids": [...], "encodings": [...], "names": [...]}
    return {"student_ids": [], "encodings": [], "names": []}


def save_master_encodings(data: dict):
    """Persist the master encodings dict to disk."""
    os.makedirs(ENCODINGS_DIR, exist_ok=True)
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)
    print(f"[INFO] Encodings saved → {ENCODINGS_FILE}")


def capture_face_samples(student_id: str, student_name: str) -> list:
    """
    Open webcam and capture SAMPLES_NEEDED face images.
    Returns list of RGB face encodings.
    """
    student_dir = os.path.join(DATASET_DIR, student_id)
    os.makedirs(student_dir, exist_ok=True)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("[ERROR] Cannot open camera. Check CAMERA_INDEX in config.py")
        return []

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    encodings_collected = []
    sample_count        = 0
    last_capture_time   = 0
    CAPTURE_INTERVAL    = 0.8   # seconds between captures

    print(f"\n[INFO] Camera opened. Look at the camera.")
    print(f"[INFO] Capturing {SAMPLES_NEEDED} face samples for {student_name} ...")
    print("[INFO] Press 'q' to cancel.\n")

    while sample_count < SAMPLES_NEEDED:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Frame read failed, retrying...")
            continue

        display = frame.copy()

        # Detect faces for live preview
        small  = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        rgb_sm = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
        locs   = face_recognition.face_locations(rgb_sm, model="hog")

        for (top, right, bottom, left) in locs:
            top    *= 2; right  *= 2
            bottom *= 2; left   *= 2
            cv2.rectangle(display, (left, top), (right, bottom), COLOR_GREEN, 2)

        # Status bar
        bar_color = COLOR_GREEN if locs else COLOR_RED
        cv2.rectangle(display, (0, 0), (640, 40), bar_color, -1)
        face_status = f"Face Detected" if locs else "No Face Detected"
        cv2.putText(display, f"{student_name} | {face_status} | Sample {sample_count}/{SAMPLES_NEEDED}",
                    (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, COLOR_WHITE, 2)

        cv2.imshow("Register Face – Press Q to cancel", display)

        # Auto-capture at interval when face is detected
        now = time.time()
        if locs and (now - last_capture_time) >= CAPTURE_INTERVAL:
            rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            enc_list = face_recognition.face_encodings(rgb_full,
                           face_recognition.face_locations(rgb_full, model=MODEL))
            if enc_list:
                encodings_collected.append(enc_list[0])
                # Save sample image
                img_path = os.path.join(student_dir, f"{student_id}_{sample_count:02d}.jpg")
                cv2.imwrite(img_path, frame)
                sample_count      += 1
                last_capture_time  = now
                print(f"  Sample {sample_count}/{SAMPLES_NEEDED} captured ✓")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[INFO] Registration cancelled by user.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return encodings_collected


def average_encoding(encodings: list) -> np.ndarray:
    """Average multiple face encodings into one representative vector."""
    return np.mean(encodings, axis=0)


# ------------------------------------------------------------------
# Main registration function
# ------------------------------------------------------------------

def register_student():
    print("\n" + "="*55)
    print("   FACE RECOGNITION ATTENDANCE – STUDENT REGISTRATION")
    print("="*55)

    # ---- Collect student details ----
    student_id = input("\nEnter Student ID (e.g. CS2021001): ").strip().upper()
    if not student_id:
        print("[ERROR] Student ID cannot be empty.")
        return

    # Check if already registered
    existing = get_student(student_id)
    if existing:
        print(f"[WARN] Student '{student_id}' already exists: {existing['name']}")
        overwrite = input("Re-register (overwrite)? (y/n): ").strip().lower()
        if overwrite != 'y':
            return

    name       = input("Enter Full Name           : ").strip().title()
    department = input("Enter Department          : ").strip().title()
    year_str   = input("Enter Year (1/2/3/4)      : ").strip()
    email      = input("Enter Email (optional)    : ").strip()
    phone      = input("Enter Phone (optional)    : ").strip()

    if not name or not department:
        print("[ERROR] Name and Department are required.")
        return

    try:
        year = int(year_str)
        if year not in (1, 2, 3, 4):
            raise ValueError
    except ValueError:
        print("[ERROR] Year must be 1, 2, 3, or 4.")
        return

    # ---- Capture face samples ----
    encodings = capture_face_samples(student_id, name)

    if len(encodings) < 3:
        print(f"\n[ERROR] Only {len(encodings)} samples captured. Need at least 3. Aborting.")
        return

    print(f"\n[INFO] {len(encodings)} samples captured. Generating encoding...")

    # ---- Build averaged encoding ----
    avg_enc = average_encoding(encodings)

    # ---- Update master encodings file ----
    master = load_master_encodings()

    # Remove old entry if re-registering
    pairs = list(zip(master["student_ids"], master["encodings"], master["names"]))
    pairs = [(sid, enc, n) for sid, enc, n in pairs if sid != student_id]

    # Add new entry
    pairs.append((student_id, avg_enc, name))

    master["student_ids"] = [p[0] for p in pairs]
    master["encodings"]   = [p[1] for p in pairs]
    master["names"]       = [p[2] for p in pairs]

    save_master_encodings(master)

    # ---- Save to database ----
    enc_rel_path = os.path.join("encodings", "encodings.pkl")
    success = add_student(student_id, name, department, year, email, phone, enc_rel_path)

    if success:
        print("\n" + "="*55)
        print(f"  ✅  {name} ({student_id}) registered successfully!")
        print(f"      Department : {department}  |  Year : {year}")
        print(f"      Samples    : {len(encodings)}")
        print("="*55 + "\n")
    else:
        print("\n[ERROR] Face encoding saved but DB insert failed. Check db.py config.")


# ------------------------------------------------------------------
# Bulk register from existing dataset folder
# (for when photos are already collected offline)
# ------------------------------------------------------------------

def register_from_dataset():
    """
    Scan dataset/<student_id>/ folders and encode any student
    not yet in the master encodings file.
    """
    if not os.path.exists(DATASET_DIR):
        print("[ERROR] Dataset directory not found.")
        return

    master = load_master_encodings()
    already = set(master["student_ids"])
    updated = False

    for student_id in os.listdir(DATASET_DIR):
        if student_id in already:
            print(f"[SKIP] {student_id} already encoded.")
            continue

        folder = os.path.join(DATASET_DIR, student_id)
        if not os.path.isdir(folder):
            continue

        images = [f for f in os.listdir(folder)
                  if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if not images:
            print(f"[WARN] No images found in dataset/{student_id}/")
            continue

        print(f"[INFO] Encoding {student_id} from {len(images)} images...")
        encodings = []
        for img_name in images:
            img_path = os.path.join(folder, img_name)
            img      = face_recognition.load_image_file(img_path)
            encs     = face_recognition.face_encodings(img, model=MODEL)
            if encs:
                encodings.append(encs[0])

        if not encodings:
            print(f"[WARN] No faces found in images for {student_id}")
            continue

        avg_enc = average_encoding(encodings)
        # Use folder name as name placeholder – update in DB later
        master["student_ids"].append(student_id)
        master["encodings"].append(avg_enc)
        master["names"].append(student_id)
        updated = True
        print(f"  ✅  {student_id} encoded ({len(encodings)} samples)")

    if updated:
        save_master_encodings(master)
    else:
        print("[INFO] Nothing new to encode.")


if __name__ == "__main__":
    register_student()
