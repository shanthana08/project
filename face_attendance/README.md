# Face Recognition Attendance System

Automatic attendance marking using face recognition.  
**Stack:** Python · OpenCV · face_recognition (dlib) · MySQL

---

## Project Structure

```
face_attendance/
├── main.py               ← Single entry point (run this)
├── attendance.py         ← Real-time face recognition + attendance marking
├── register_face.py      ← Register new student with face capture
├── view_attendance.py    ← Admin panel – view & export reports
├── db.py                 ← MySQL connection + all DB queries
├── config.py             ← All settings (DB credentials, camera, tolerance)
├── schema.sql            ← Database + table creation script
├── requirements.txt      ← Python dependencies
├── dataset/              ← Student face photo folders (auto-created)
│   └── CS2021001/        ← Photos for student CS2021001
├── encodings/
│   └── encodings.pkl     ← Master face encodings file (auto-generated)
└── reports/              ← Exported CSV attendance reports
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.9 – 3.11 |
| MySQL | 8.0+ |
| Webcam | Any USB/built-in |
| CMake | Required for dlib |

---

## Setup Guide

### Step 1 – Clone / Download the project

Place the `face_attendance/` folder anywhere on your machine.

---

### Step 2 – Install dlib (Windows)

`dlib` needs a pre-built wheel on Windows (compiling from source requires Visual Studio):

1. Go to → https://github.com/z-mahmud22/Dlib_Windows_Python3.x/releases
2. Download the `.whl` matching your Python version (e.g. `dlib-19.24.1-cp311-cp311-win_amd64.whl` for Python 3.11)
3. Install it:
   ```bash
   pip install dlib-19.24.1-cp311-cp311-win_amd64.whl
   ```

---

### Step 3 – Install Python dependencies

```bash
pip install -r requirements.txt
```

---

### Step 4 – Set up MySQL database

1. Open MySQL Workbench or any MySQL client.
2. Run the schema file:
   ```sql
   source /path/to/face_attendance/schema.sql
   ```
   Or paste the contents of `schema.sql` and execute.

---

### Step 5 – Configure database credentials

Open `config.py` and update:

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",          # ← your MySQL username
    "password": "yourpassword",  # ← your MySQL password
    "database": "face_attendance_db",
}
```

---

### Step 6 – Run the application

```bash
python main.py
```

---

## How to Use

### Register a Student

1. Run `python main.py` → select option **2**
2. Enter student details (ID, Name, Department, Year, Email, Phone)
3. Look at the webcam – it will auto-capture **10 face samples**
4. Face encoding is saved to `encodings/encodings.pkl`
5. Student record is saved to MySQL

**Dataset folder structure created automatically:**
```
dataset/
└── CS2021001/
    ├── CS2021001_00.jpg
    ├── CS2021001_01.jpg
    ...
```

---

### Take Attendance

1. Run `python main.py` → select option **1**
2. Choose the subject
3. Optionally enter class start time (for late detection)
4. System opens webcam — students walk in front of the camera
5. Each recognized face is automatically marked in MySQL
6. Duplicate marking is prevented (cooldown: 30 seconds)
7. Press **Q** to end session → CSV is auto-exported to `reports/`

**On-screen indicators:**
| Color | Meaning |
|-------|---------|
| 🟢 Green box | Face recognized + attendance marked |
| 🟡 Yellow box | Already marked (no duplicate) |
| 🔴 Red box | Unknown face |

---

### View Reports (Admin Panel)

1. Run `python main.py` → select option **3**

Available options:
- Today's attendance
- Attendance by date
- Attendance by subject
- Individual student report
- Overall attendance % summary
- Last 7 days report
- Export any report as CSV

---

## Configuration Reference (`config.py`)

| Setting | Default | Description |
|---------|---------|-------------|
| `TOLERANCE` | `0.5` | Face match strictness (lower = stricter) |
| `MODEL` | `"hog"` | `"hog"` = fast CPU, `"cnn"` = accurate GPU |
| `FRAME_RESIZE` | `0.5` | Frame scale for processing speed |
| `CAMERA_INDEX` | `0` | 0 = default webcam |
| `COOLDOWN_SECONDS` | `30` | Min seconds between re-marks |
| `LATE_THRESHOLD_MINUTES` | `15` | Minutes after start to mark as "Late" |

---

## Database Tables

| Table | Purpose |
|-------|---------|
| `students` | Student registration details + encoding path |
| `attendance` | One row per student per class session |
| `subjects` | Subject master list |
| `v_daily_summary` | View: daily attendance summary |
| `v_student_percentage` | View: attendance % per student |

---

## Troubleshooting

**Camera not opening**
- Check `CAMERA_INDEX` in `config.py` (try 1 or 2 for USB cams)

**dlib installation fails**
- Use pre-built wheel from the link above
- Do NOT try `pip install dlib` directly on Windows without CMake + Visual Studio

**Face not detected**
- Ensure good lighting
- Face should be 30–200 cm from camera
- Reduce `TOLERANCE` value (e.g. 0.45) for stricter matching

**DB connection error**
- Verify MySQL service is running: `services.msc` → MySQL80
- Double-check credentials in `config.py`
- Confirm `schema.sql` was executed

**Unknown face even after registration**
- Re-register with better lighting
- Capture samples from multiple angles
- Lower `TOLERANCE` to 0.45

---

## Credits

Built with:
- [face_recognition](https://github.com/ageitgey/face_recognition) by Adam Geitgey
- [OpenCV](https://opencv.org/)
- [dlib](http://dlib.net/) by Davis King
- [MySQL Connector/Python](https://dev.mysql.com/doc/connector-python/)

---

*College Project – Face Recognition Attendance System*
