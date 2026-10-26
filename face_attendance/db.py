# ============================================================
#  db.py  –  MySQL connection pool & helper functions
# ============================================================

import mysql.connector
from mysql.connector import pooling, Error
from datetime import datetime, date, time as dtime
import logging

from config import DB_CONFIG, LATE_THRESHOLD_MINUTES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Connection pool (reuse connections instead of open/close each time)
# ------------------------------------------------------------------
_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="face_att_pool",
            pool_size=5,
            **DB_CONFIG
        )
    return _pool


def get_connection():
    """Return a connection from the pool."""
    return get_pool().get_connection()


# ------------------------------------------------------------------
# Student helpers
# ------------------------------------------------------------------

def add_student(student_id: str, name: str, department: str, year: int,
                email: str = "", phone: str = "", encoding_file: str = "") -> bool:
    """Insert a new student record. Returns True on success."""
    sql = """
        INSERT INTO students (student_id, name, department, year, email, phone, encoding_file)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            name=VALUES(name), department=VALUES(department),
            year=VALUES(year), email=VALUES(email),
            phone=VALUES(phone), encoding_file=VALUES(encoding_file)
    """
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(sql, (student_id, name, department, year, email, phone, encoding_file))
        conn.commit()
        logger.info(f"Student saved: {student_id} – {name}")
        return True
    except Error as e:
        logger.error(f"add_student error: {e}")
        return False
    finally:
        try: cur.close(); conn.close()
        except: pass


def get_all_students() -> list:
    """Return list of all active students as dicts."""
    sql = "SELECT student_id, name, department, year, email, phone FROM students WHERE is_active=1"
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(sql)
        return cur.fetchall()
    except Error as e:
        logger.error(f"get_all_students error: {e}")
        return []
    finally:
        try: cur.close(); conn.close()
        except: pass


def get_student(student_id: str) -> dict | None:
    """Return a single student dict or None."""
    sql = "SELECT * FROM students WHERE student_id=%s AND is_active=1"
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(sql, (student_id,))
        return cur.fetchone()
    except Error as e:
        logger.error(f"get_student error: {e}")
        return None
    finally:
        try: cur.close(); conn.close()
        except: pass


# ------------------------------------------------------------------
# Attendance helpers
# ------------------------------------------------------------------

def mark_attendance(student_id: str, student_name: str, department: str,
                    subject: str = "General",
                    class_start: dtime | None = None) -> str:
    """
    Mark attendance for a student.
    Returns: 'marked'  – successfully inserted
             'already' – already marked today for this subject
             'error'   – DB error
    """
    today    = date.today()
    now_time = datetime.now().time()

    # Determine Present / Late
    status = "Present"
    if class_start:
        delta = (datetime.combine(today, now_time) -
                 datetime.combine(today, class_start)).total_seconds() / 60
        if delta > LATE_THRESHOLD_MINUTES:
            status = "Late"

    sql = """
        INSERT INTO attendance (student_id, student_name, department, date, time_in, subject, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(sql, (student_id, student_name, department,
                          today, now_time, subject, status))
        conn.commit()
        logger.info(f"Attendance marked: {student_id} | {subject} | {status}")
        return "marked"
    except mysql.connector.IntegrityError:
        # Duplicate key – already marked
        return "already"
    except Error as e:
        logger.error(f"mark_attendance error: {e}")
        return "error"
    finally:
        try: cur.close(); conn.close()
        except: pass


def get_attendance_by_date(target_date: date | None = None,
                           subject: str | None = None) -> list:
    """Fetch attendance records filtered by date and/or subject."""
    if target_date is None:
        target_date = date.today()

    conditions = ["date = %s"]
    params     = [target_date]

    if subject:
        conditions.append("subject = %s")
        params.append(subject)

    sql = f"""
        SELECT student_id, student_name, department, date, time_in, subject, status
        FROM attendance
        WHERE {' AND '.join(conditions)}
        ORDER BY time_in ASC
    """
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        return cur.fetchall()
    except Error as e:
        logger.error(f"get_attendance_by_date error: {e}")
        return []
    finally:
        try: cur.close(); conn.close()
        except: pass


def get_student_attendance(student_id: str) -> list:
    """All attendance records for one student."""
    sql = """
        SELECT date, time_in, subject, status
        FROM attendance
        WHERE student_id = %s
        ORDER BY date DESC, time_in DESC
    """
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(sql, (student_id,))
        return cur.fetchall()
    except Error as e:
        logger.error(f"get_student_attendance error: {e}")
        return []
    finally:
        try: cur.close(); conn.close()
        except: pass


def get_attendance_summary() -> list:
    """Return rows from v_student_percentage view."""
    sql = "SELECT * FROM v_student_percentage ORDER BY department, year, name"
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(sql)
        return cur.fetchall()
    except Error as e:
        logger.error(f"get_attendance_summary error: {e}")
        return []
    finally:
        try: cur.close(); conn.close()
        except: pass


def get_subjects() -> list:
    """Return all subjects."""
    sql = "SELECT code, name, department, year FROM subjects ORDER BY department, year, name"
    try:
        conn = get_connection()
        cur  = conn.cursor(dictionary=True)
        cur.execute(sql)
        return cur.fetchall()
    except Error as e:
        logger.error(f"get_subjects error: {e}")
        return []
    finally:
        try: cur.close(); conn.close()
        except: pass


# ------------------------------------------------------------------
# DB health check
# ------------------------------------------------------------------

def test_connection() -> bool:
    """Ping the DB and return True if OK."""
    try:
        conn = get_connection()
        conn.ping(reconnect=True)
        conn.close()
        logger.info("Database connection: OK")
        return True
    except Error as e:
        logger.error(f"DB connection failed: {e}")
        return False
