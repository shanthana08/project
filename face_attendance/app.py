# ============================================================
#  app.py  –  Flask Web Application
#  Run:  python app.py
#  Open: http://localhost:5000
# ============================================================

import os, sys, cv2, pickle, threading, time, csv, io
import numpy as np
import face_recognition
from datetime import date, datetime
from flask import (Flask, render_template, request, jsonify,
                   Response, redirect, url_for, send_file, flash)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    ENCODINGS_FILE, DATASET_DIR, ENCODINGS_DIR, REPORTS_DIR,
    CAMERA_INDEX, MODEL, FRAME_RESIZE, TOLERANCE,
    COOLDOWN_SECONDS, UNKNOWN_LABEL,
    COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_WHITE, COLOR_BLACK
)
from db import (
    test_connection, add_student, get_all_students, get_student,
    mark_attendance, get_attendance_by_date, get_student_attendance,
    get_attendance_summary, get_subjects
)
from register_face import (
    load_master_encodings, save_master_encodings, average_encoding
)

# ── Flask app ──────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "face_att_secret_2024"

# ── Global camera state ────────────────────────────────────
camera_lock       = threading.Lock()
active_camera     = None          # cv2.VideoCapture instance
attendance_log    = []            # live log list for SSE
session_subject   = "General"
session_marked    = set()
session_cooldown  = {}
stream_active     = False

# ── Helpers ────────────────────────────────────────────────

def get_camera():
    global active_camera
    if active_camera is None or not active_camera.isOpened():
        active_camera = cv2.VideoCapture(CAMERA_INDEX)
        active_camera.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
        active_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return active_camera


def release_camera():
    global active_camera, stream_active
    stream_active = False
    if active_camera and active_camera.isOpened():
        active_camera.release()
    active_camera = None


def load_encodings():
    if not os.path.exists(ENCODINGS_FILE):
        return None
    with open(ENCODINGS_FILE, "rb") as f:
        return pickle.load(f)


# ── Dashboard ──────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    students  = get_all_students()
    today_att = get_attendance_by_date(date.today())
    summary   = get_attendance_summary()
    subjects  = get_subjects()

    # Stats
    total_students  = len(students)
    present_today   = len(today_att)
    absent_today    = max(total_students - present_today, 0)
    late_today      = sum(1 for r in today_att if r.get("status") == "Late")

    # Dept breakdown for chart
    dept_map: dict = {}
    for r in today_att:
        dept_map[r["department"]] = dept_map.get(r["department"], 0) + 1

    return render_template("dashboard.html",
        total_students  = total_students,
        present_today   = present_today,
        absent_today    = absent_today,
        late_today      = late_today,
        today_att       = today_att[:10],   # latest 10
        dept_labels     = list(dept_map.keys()),
        dept_data       = list(dept_map.values()),
        subjects        = subjects,
    )


# ── Students ────────────────────────────────────────────────

@app.route("/students")
def students_page():
    students = get_all_students()
    return render_template("students.html", students=students)


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    """
    Expects JSON:
      { student_id, name, department, year, email, phone,
        images: [ base64_jpeg, ... ] }
    """
    data = request.get_json(force=True)
    required = ["student_id", "name", "department", "year", "images"]
    for f in required:
        if not data.get(f):
            return jsonify(success=False, message=f"'{f}' is required"), 400

    student_id = str(data["student_id"]).strip().upper()
    name       = str(data["name"]).strip().title()
    department = str(data["department"]).strip().title()
    year       = int(data["year"])
    email      = str(data.get("email", "")).strip()
    phone      = str(data.get("phone", "")).strip()
    images_b64 = data["images"]          # list of base64 strings

    if not images_b64 or len(images_b64) < 3:
        return jsonify(success=False,
                       message="Need at least 3 face images"), 400

    # Decode images and extract encodings
    import base64
    encodings_list = []
    student_dir    = os.path.join(DATASET_DIR, student_id)
    os.makedirs(student_dir, exist_ok=True)

    for idx, b64_str in enumerate(images_b64):
        try:
            # Strip data-url prefix if present
            if "," in b64_str:
                b64_str = b64_str.split(",")[1]
            img_bytes = base64.b64decode(b64_str)
            np_arr    = np.frombuffer(img_bytes, np.uint8)
            frame     = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            # Save sample
            img_path = os.path.join(student_dir, f"{student_id}_{idx:02d}.jpg")
            cv2.imwrite(img_path, frame)

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = face_recognition.face_locations(rgb, model=MODEL)
            encs = face_recognition.face_encodings(rgb, locs)
            if encs:
                encodings_list.append(encs[0])
        except Exception as e:
            continue

    if len(encodings_list) < 3:
        return jsonify(success=False,
                       message=f"Only {len(encodings_list)} valid face(s) detected. "
                               f"Need at least 3. Ensure good lighting and face clearly visible."), 400

    # Average encoding
    avg_enc = average_encoding(encodings_list)

    # Update master pickle
    master = load_master_encodings()
    pairs  = [(s, e, n) for s, e, n in
              zip(master["student_ids"], master["encodings"], master["names"])
              if s != student_id]
    pairs.append((student_id, avg_enc, name))
    master["student_ids"] = [p[0] for p in pairs]
    master["encodings"]   = [p[1] for p in pairs]
    master["names"]       = [p[2] for p in pairs]
    save_master_encodings(master)

    # Save to DB
    enc_path = os.path.join("encodings", "encodings.pkl")
    ok = add_student(student_id, name, department, year, email, phone, enc_path)
    if ok:
        return jsonify(success=True,
                       message=f"{name} registered successfully!",
                       samples=len(encodings_list))
    else:
        return jsonify(success=False,
                       message="DB error – check config.py credentials"), 500


# ── Live Attendance ─────────────────────────────────────────

@app.route("/attendance")
def attendance_page():
    subjects = get_subjects()
    return render_template("attendance.html", subjects=subjects)


@app.route("/api/start_session", methods=["POST"])
def api_start_session():
    global session_subject, session_marked, session_cooldown, stream_active, attendance_log
    data             = request.get_json(force=True)
    session_subject  = data.get("subject", "General")
    session_marked   = set()
    session_cooldown = {}
    attendance_log   = []
    stream_active    = True
    return jsonify(success=True, subject=session_subject)


@app.route("/api/stop_session", methods=["POST"])
def api_stop_session():
    global stream_active
    stream_active = False
    release_camera()
    return jsonify(success=True, marked=len(session_marked))


def generate_frames():
    """Generator that yields MJPEG frames for /video_feed."""
    global session_marked, session_cooldown, attendance_log, stream_active

    data = load_encodings()
    if data is None:
        return

    known_encodings = data["encodings"]
    known_ids       = data["student_ids"]
    known_names     = data["names"]

    face_labels  = {}
    process_this = True

    cap = get_camera()

    while stream_active:
        with camera_lock:
            ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue

        if process_this:
            small  = cv2.resize(frame, (0, 0), fx=FRAME_RESIZE, fy=FRAME_RESIZE)
            rgb_sm = cv2.cvtColor(small, cv2.COLOR_BGR2RGB)
            locs   = face_recognition.face_locations(rgb_sm, model="hog")
            encs   = face_recognition.face_encodings(rgb_sm, locs)
            face_labels = {}

            for enc, loc in zip(encs, locs):
                top, right, bottom, left = [int(v / FRAME_RESIZE) for v in loc]
                distances = face_recognition.face_distance(known_encodings, enc)

                name = UNKNOWN_LABEL; sid = ""; status = "unknown"

                if len(distances) > 0:
                    best = int(np.argmin(distances))
                    if distances[best] <= TOLERANCE:
                        sid  = known_ids[best]
                        name = known_names[best]
                        now  = time.time()

                        if (now - session_cooldown.get(sid, 0)) >= COOLDOWN_SECONDS:
                            student = get_student(sid)
                            dept    = student["department"] if student else "Unknown"
                            result  = mark_attendance(sid, name, dept, session_subject)
                            session_cooldown[sid] = now

                            if result == "marked":
                                session_marked.add(sid)
                                status = "marked"
                                log_entry = {
                                    "sid": sid, "name": name,
                                    "status": "Present",
                                    "time": datetime.now().strftime("%H:%M:%S")
                                }
                                attendance_log.append(log_entry)
                            elif result == "already":
                                session_marked.add(sid)
                                status = "already"
                        else:
                            status = "already"
                            session_marked.add(sid)

                face_labels[(top, right, bottom, left)] = (name, sid, status)

        process_this = not process_this

        # Draw overlays
        for (top, right, bottom, left), (name, sid, status) in face_labels.items():
            if name == UNKNOWN_LABEL:
                color = COLOR_RED
                label = "Unknown"
            elif status == "already":
                color = COLOR_YELLOW
                label = f"{name} | Already Marked"
            else:
                color = COLOR_GREEN
                label = f"{name} | Marked ✓"

            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom), (right, bottom + 28), color, cv2.FILLED)
            cv2.putText(frame, label, (left + 4, bottom + 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_WHITE, 1)

        # Top bar
        cv2.rectangle(frame, (0, 0), (640, 38), (30, 30, 30), -1)
        cv2.putText(frame,
                    f"Subject: {session_subject}  |  Marked: {len(session_marked)}  |  "
                    f"{datetime.now().strftime('%H:%M:%S')}",
                    (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLOR_WHITE, 1)

        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

    release_camera()


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/api/attendance_log")
def api_attendance_log():
    """Poll endpoint – returns new entries since last check."""
    since = int(request.args.get("since", 0))
    new   = attendance_log[since:]
    return jsonify(entries=new, total=len(attendance_log))


@app.route("/api/session_stats")
def api_session_stats():
    return jsonify(
        marked  = len(session_marked),
        subject = session_subject,
        active  = stream_active
    )


# ── Reports ─────────────────────────────────────────────────

@app.route("/reports")
def reports_page():
    students = get_all_students()
    subjects = get_subjects()
    return render_template("reports.html",
                           students=students, subjects=subjects)


@app.route("/api/report/today")
def api_report_today():
    subject = request.args.get("subject") or None
    records = get_attendance_by_date(date.today(), subject)
    return jsonify(records=[_serialize(r) for r in records])


@app.route("/api/report/date")
def api_report_date():
    date_str = request.args.get("date", str(date.today()))
    subject  = request.args.get("subject") or None
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify(error="Invalid date"), 400
    records = get_attendance_by_date(target, subject)
    return jsonify(records=[_serialize(r) for r in records])


@app.route("/api/report/student")
def api_report_student():
    sid     = request.args.get("student_id", "").upper()
    records = get_student_attendance(sid)
    return jsonify(records=[_serialize(r) for r in records])


@app.route("/api/report/summary")
def api_report_summary():
    records = get_attendance_summary()
    return jsonify(records=[_serialize(r) for r in records])


@app.route("/api/students/all")
def api_students_all():
    return jsonify(students=get_all_students())


@app.route("/api/export/csv")
def api_export_csv():
    """Build CSV in-memory and stream to browser."""
    report_type = request.args.get("type", "today")
    date_str    = request.args.get("date", str(date.today()))
    subject     = request.args.get("subject") or None
    student_id  = request.args.get("student_id", "").upper()

    if report_type == "today":
        records  = get_attendance_by_date(date.today(), subject)
        filename = f"attendance_today_{date.today()}.csv"
    elif report_type == "date":
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return "Invalid date", 400
        records  = get_attendance_by_date(target, subject)
        filename = f"attendance_{date_str}.csv"
    elif report_type == "student":
        records  = get_student_attendance(student_id)
        filename = f"student_{student_id}.csv"
    elif report_type == "summary":
        records  = get_attendance_summary()
        filename = f"summary_all_{date.today()}.csv"
    else:
        return "Unknown report type", 400

    if not records:
        return "No records found", 404

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[_str_key(k) for k in records[0].keys()])
    writer.writeheader()
    for row in records:
        writer.writerow({_str_key(k): str(v) for k, v in row.items()})
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ── API helpers ─────────────────────────────────────────────

def _serialize(obj):
    """Convert date/time objects to strings for JSON."""
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj


def _str_key(k):
    return str(k)


# ── Health check ────────────────────────────────────────────

@app.route("/api/health")
def api_health():
    db_ok = test_connection()
    enc   = os.path.exists(ENCODINGS_FILE)
    return jsonify(db=db_ok, encodings=enc,
                   students=len(get_all_students()))


# ── Run ─────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(DATASET_DIR,   exist_ok=True)
    os.makedirs(ENCODINGS_DIR, exist_ok=True)
    os.makedirs(REPORTS_DIR,   exist_ok=True)
    print("\n" + "="*50)
    print("  Face Attendance Web App")
    print("  Open → http://localhost:5000")
    print("="*50 + "\n")
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True,
            use_reloader=False)   # use_reloader=False avoids double camera init
