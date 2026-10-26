# ============================================================
#  main.py  –  Single entry point for the entire system
#
#  Usage:
#    python main.py
# ============================================================

import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db import test_connection


# ------------------------------------------------------------------
# ASCII banner
# ------------------------------------------------------------------

BANNER = r"""
 ███████╗ █████╗  ██████╗███████╗    ██████╗ ███████╗ ██████╗
 ██╔════╝██╔══██╗██╔════╝██╔════╝    ██╔══██╗██╔════╝██╔════╝
 █████╗  ███████║██║     █████╗      ██████╔╝█████╗  ██║
 ██╔══╝  ██╔══██║██║     ██╔══╝      ██╔══██╗██╔══╝  ██║
 ██║     ██║  ██║╚██████╗███████╗    ██║  ██║███████╗╚██████╗
 ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝    ╚═╝  ╚═╝╚══════╝ ╚═════╝

    ATTENDANCE SYSTEM  |  Python + OpenCV + face_recognition + MySQL
"""


def print_menu():
    print("\n" + "─" * 55)
    print("  MAIN MENU")
    print("─" * 55)
    print("  1.  Start Attendance Session  (Face Recognition)")
    print("  2.  Register New Student      (with Face Capture)")
    print("  3.  View / Export Reports     (Admin Panel)")
    print("  4.  Test Database Connection")
    print("  0.  Exit")
    print("─" * 55)


def main():
    print(BANNER)

    # Quick DB check at startup
    print("[INFO] Checking database connection...")
    if not test_connection():
        print("\n[ERROR] Database connection failed!")
        print("  → Make sure MySQL is running.")
        print("  → Check credentials in config.py")
        print("  → Run schema.sql to create the database.\n")
        ans = input("Continue anyway? (y/n): ").strip().lower()
        if ans != 'y':
            sys.exit(1)

    while True:
        print_menu()
        choice = input("\nEnter choice: ").strip()

        if choice == "1":
            # ---- Attendance session ----
            from attendance import run_attendance

            print("\n─ Subject Selection ─")
            subjects = [
                "General",
                "CS301-Data Structures",
                "CS302-Operating Systems",
                "CS303-Database Management",
                "CS401-Machine Learning",
                "CS402-Computer Networks",
            ]
            for i, s in enumerate(subjects, 1):
                print(f"  {i}. {s}")
            print(f"  {len(subjects)+1}. Custom subject")

            ch = input("Select: ").strip()
            try:
                idx = int(ch) - 1
                if 0 <= idx < len(subjects):
                    subject = subjects[idx]
                else:
                    subject = input("Enter subject name: ").strip() or "General"
            except ValueError:
                subject = "General"

            class_start = input("Class start time HH:MM (or Enter to skip): ").strip()
            run_attendance(subject, class_start or None)

        elif choice == "2":
            # ---- Register student ----
            from register_face import register_student
            register_student()

        elif choice == "3":
            # ---- Admin / Reports ----
            from view_attendance import admin_menu
            admin_menu()

        elif choice == "4":
            # ---- DB test ----
            ok = test_connection()
            if ok:
                print("[OK] Database is connected and reachable.")
            else:
                print("[FAIL] Cannot reach database. Check config.py")

        elif choice == "0":
            print("\nGoodbye! 👋\n")
            break

        else:
            print("[ERROR] Invalid choice. Enter 0-4.")


if __name__ == "__main__":
    main()
