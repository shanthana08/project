-- ============================================================
--  Face Recognition Attendance System - Database Schema
--  Run this file once to set up the MySQL database
-- ============================================================

CREATE DATABASE IF NOT EXISTS face_attendance_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE face_attendance_db;

-- -------------------------------------------------------
-- Table: students
--   Stores student registration details and face encodings
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS students (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    student_id    VARCHAR(20)  NOT NULL UNIQUE,   -- e.g. "CS2021001"
    name          VARCHAR(100) NOT NULL,
    department    VARCHAR(100) NOT NULL,
    year          TINYINT      NOT NULL,           -- 1 / 2 / 3 / 4
    email         VARCHAR(150),
    phone         VARCHAR(15),
    encoding_file VARCHAR(255),                    -- path to .pkl file
    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active     TINYINT(1) DEFAULT 1
);

-- -------------------------------------------------------
-- Table: attendance
--   One row per student per class session
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    student_id    VARCHAR(20)  NOT NULL,
    student_name  VARCHAR(100) NOT NULL,
    department    VARCHAR(100) NOT NULL,
    date          DATE         NOT NULL,
    time_in       TIME         NOT NULL,
    subject       VARCHAR(100) DEFAULT 'General',
    status        ENUM('Present','Absent','Late') DEFAULT 'Present',
    marked_by     VARCHAR(50)  DEFAULT 'FaceRecognition',
    created_at    DATETIME     DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(student_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    -- Prevent duplicate entry for same student on same date+subject
    UNIQUE KEY uq_attendance (student_id, date, subject)
);

-- -------------------------------------------------------
-- Table: subjects
--   Master list of subjects (optional, for dropdown)
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS subjects (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    code       VARCHAR(20)  NOT NULL UNIQUE,
    name       VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    year       TINYINT      NOT NULL
);

-- -------------------------------------------------------
-- Sample seed data (optional - remove in production)
-- -------------------------------------------------------
INSERT IGNORE INTO subjects (code, name, department, year) VALUES
    ('CS301', 'Data Structures',        'Computer Science', 3),
    ('CS302', 'Operating Systems',      'Computer Science', 3),
    ('CS303', 'Database Management',    'Computer Science', 3),
    ('CS401', 'Machine Learning',       'Computer Science', 4),
    ('CS402', 'Computer Networks',      'Computer Science', 4);

-- -------------------------------------------------------
-- Useful views
-- -------------------------------------------------------

-- Daily attendance summary
CREATE OR REPLACE VIEW v_daily_summary AS
SELECT
    a.date,
    a.subject,
    a.department,
    COUNT(*)                                        AS total_present,
    GROUP_CONCAT(a.student_name ORDER BY a.student_name SEPARATOR ', ')
                                                    AS students_present
FROM attendance a
WHERE a.status = 'Present'
GROUP BY a.date, a.subject, a.department;

-- Student-wise attendance percentage
CREATE OR REPLACE VIEW v_student_percentage AS
SELECT
    s.student_id,
    s.name,
    s.department,
    s.year,
    COUNT(a.id)                                     AS classes_attended,
    ROUND(COUNT(a.id) * 100.0 /
          NULLIF((SELECT COUNT(DISTINCT date) FROM attendance
                  WHERE department = s.department), 0), 2)
                                                    AS attendance_pct
FROM students s
LEFT JOIN attendance a ON s.student_id = a.student_id AND a.status = 'Present'
WHERE s.is_active = 1
GROUP BY s.student_id, s.name, s.department, s.year;
