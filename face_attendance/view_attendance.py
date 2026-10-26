# ============================================================
#  view_attendance.py  –  Admin console to view & export reports
# ============================================================

import os
import csv
from datetime import date, datetime, timedelta
from tabulate import tabulate   # pip install tabulate

from db import (
    get_attendance_by_date,
    get_student_attendance,
    get_attendance_summary,
    get_all_students,
    get_subjects,
)
from config import REPORTS_DIR


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _hr(char="─", width=60):
    print(char * width)


def _header(title: str):
    _hr()
    print(f"  {title.upper()}")
    _hr()


def export_to_csv(records: list, filename: str) -> str:
    """Write records list-of-dicts to a CSV file. Returns filepath."""
    if not records:
        print("[INFO] No records to export.")
        return ""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)
    print(f"[INFO] Exported → {filepath}")
    return filepath


def format_records(records: list) -> str:
    """Pretty-print list of dicts as a table."""
    if not records:
        return "  (no records found)"
    return tabulate(records, headers="keys", tablefmt="rounded_outline")


# ------------------------------------------------------------------
# View functions
# ------------------------------------------------------------------

def view_today():
    """Show all attendance for today."""
    _header(f"Today's Attendance  ({date.today()})")
    records = get_attendance_by_date(date.today())
    print(format_records(records))
    print(f"\n  Total present: {len(records)}")


def view_by_date():
    """Ask for a date and show attendance."""
    date_str = input("Enter date (YYYY-MM-DD): ").strip()
    try:
        target = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print("[ERROR] Invalid date format.")
        return

    subject = input("Filter by subject (or press Enter for all): ").strip() or None
    _header(f"Attendance on {target}" + (f" | {subject}" if subject else ""))
    records = get_attendance_by_date(target, subject)
    print(format_records(records))
    print(f"\n  Total present: {len(records)}")

    # Offer export
    if records:
        ans = input("\nExport to CSV? (y/n): ").strip().lower()
        if ans == 'y':
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"att_{date_str}_{ts}.csv"
            export_to_csv(records, filename)


def view_by_subject():
    """Filter attendance for today by subject."""
    subjects = get_subjects()
    if not subjects:
        print("[WARN] No subjects in DB. Enter manually.")
        subject = input("Subject name: ").strip()
    else:
        print("\nSubjects:")
        for i, s in enumerate(subjects, 1):
            print(f"  {i}. {s['code']} – {s['name']}")
        choice = input("Select number: ").strip()
        try:
            idx     = int(choice) - 1
            subject = subjects[idx]["code"] if 0 <= idx < len(subjects) else None
        except (ValueError, IndexError):
            subject = None

    if not subject:
        return

    date_str = input("Date (YYYY-MM-DD) or Enter for today: ").strip()
    if date_str:
        try:
            target = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            print("[ERROR] Invalid date.")
            return
    else:
        target = date.today()

    _header(f"Attendance | {subject} | {target}")
    records = get_attendance_by_date(target, subject)
    print(format_records(records))
    print(f"\n  Total: {len(records)}")


def view_student_report():
    """Show all attendance for one student."""
    student_id = input("Enter Student ID: ").strip().upper()
    if not student_id:
        return

    _header(f"Attendance Report – {student_id}")
    records = get_student_attendance(student_id)
    print(format_records(records))
    print(f"\n  Total sessions attended: {len(records)}")

    if records:
        ans = input("\nExport to CSV? (y/n): ").strip().lower()
        if ans == 'y':
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"student_{student_id}_{ts}.csv"
            export_to_csv(records, filename)


def view_summary():
    """Show attendance percentage per student (from DB view)."""
    _header("Attendance Summary – All Students")
    records = get_attendance_summary()
    print(format_records(records))

    if records:
        ans = input("\nExport to CSV? (y/n): ").strip().lower()
        if ans == 'y':
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_all_{ts}.csv"
            export_to_csv(records, filename)


def view_all_students():
    """List all registered students."""
    _header("Registered Students")
    students = get_all_students()
    print(format_records(students))
    print(f"\n  Total registered: {len(students)}")


def view_last_7_days():
    """Show attendance for the past 7 days."""
    _header("Attendance – Last 7 Days")
    today   = date.today()
    all_rec = []
    for i in range(7):
        day  = today - timedelta(days=i)
        recs = get_attendance_by_date(day)
        all_rec.extend(recs)

    print(format_records(all_rec))
    print(f"\n  Total records: {len(all_rec)}")

    if all_rec:
        ans = input("\nExport to CSV? (y/n): ").strip().lower()
        if ans == 'y':
            ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"last7days_{ts}.csv"
            export_to_csv(all_rec, filename)


def export_all_today():
    """Export all today's records to CSV directly."""
    records  = get_attendance_by_date(date.today())
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"attendance_today_{ts}.csv"
    export_to_csv(records, filename)


# ------------------------------------------------------------------
# Admin menu
# ------------------------------------------------------------------

MENU = [
    ("View today's attendance",          view_today),
    ("View by date",                     view_by_date),
    ("View by subject",                  view_by_subject),
    ("View student report",              view_student_report),
    ("View attendance summary (% all)",  view_summary),
    ("View all registered students",     view_all_students),
    ("View last 7 days",                 view_last_7_days),
    ("Export today to CSV",              export_all_today),
]


def admin_menu():
    while True:
        print("\n")
        _header("ATTENDANCE ADMIN PANEL")
        for i, (label, _) in enumerate(MENU, 1):
            print(f"  {i}. {label}")
        print(f"  0. Exit")
        _hr()

        choice = input("Select option: ").strip()
        if choice == "0":
            print("Goodbye!")
            break
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(MENU):
                MENU[idx][1]()
            else:
                print("[ERROR] Invalid choice.")
        except ValueError:
            print("[ERROR] Enter a number.")


if __name__ == "__main__":
    admin_menu()
