#!/usr/bin/env python3
"""
Student Result Manager
A feature-rich command-line student records application using SQLite.

Python: 3.10+
Dependencies: Python standard library only.
Run: python student_result_manager.py
"""

from __future__ import annotations

import csv
import json
import logging
import math
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

APP_NAME = "STUDENT RESULT MANAGER"
APP_VERSION = "2.0.0"
ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "students.db"
LOG_PATH = DATA_DIR / "app.log"
BACKUP_DIR = DATA_DIR / "backups"
DEFAULT_SUBJECTS = ("Physics", "Chemistry", "Mathematics")
PASS_MARK = 33.0
MAX_MARK = 100.0

DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("student_result_manager")


class AppError(Exception):
    """Base class for expected application errors."""


class ValidationError(AppError):
    """Raised when user input or imported data is invalid."""


class StudentNotFoundError(AppError):
    """Raised when a requested student does not exist."""


@dataclass(frozen=True)
class Student:
    id: int
    name: str
    roll_number: str
    class_name: str
    physics: float
    chemistry: float
    mathematics: float
    created_at: str
    updated_at: str

    @property
    def total(self) -> float:
        return self.physics + self.chemistry + self.mathematics

    @property
    def percentage(self) -> float:
        return self.total / len(DEFAULT_SUBJECTS)

    @property
    def grade(self) -> str:
        if min(self.physics, self.chemistry, self.mathematics) < PASS_MARK:
            return "F"
        pct = self.percentage
        if pct >= 90:
            return "A+"
        if pct >= 80:
            return "A"
        if pct >= 70:
            return "B"
        if pct >= 60:
            return "C"
        if pct >= 50:
            return "D"
        return "E"

    @property
    def result(self) -> str:
        return "PASS" if min(
            self.physics, self.chemistry, self.mathematics
        ) >= PASS_MARK else "FAIL"


class Database:
    """Owns database connections and creates the schema when needed."""

    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as con:
            con.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE,
                    roll_number TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    class_name TEXT NOT NULL DEFAULT 'First Year',
                    physics REAL NOT NULL CHECK (physics BETWEEN 0 AND 100),
                    chemistry REAL NOT NULL CHECK (chemistry BETWEEN 0 AND 100),
                    mathematics REAL NOT NULL CHECK (mathematics BETWEEN 0 AND 100),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            con.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    student_roll TEXT,
                    details TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_students_name
                ON students(name)
            """)
            con.execute("""
                CREATE INDEX IF NOT EXISTS idx_students_class
                ON students(class_name)
            """)

    def audit(self, action: str, roll: str | None, details: str) -> None:
        with self.connect() as con:
            con.execute(
                "INSERT INTO audit_log(action, student_roll, details, timestamp) "
                "VALUES (?, ?, ?, ?)",
                (action, roll, details, now()),
            )


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def clean_text(value: object, field: str, max_length: int = 100) -> str:
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field} cannot be empty.")
    if len(text) > max_length:
        raise ValidationError(f"{field} must be at most {max_length} characters.")
    if "\n" in text or "\r" in text:
        raise ValidationError(f"{field} cannot contain a newline.")
    return text


def validate_mark(value: object, subject: str) -> float:
    try:
        mark = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{subject} marks must be a number.") from None
    if not math.isfinite(mark):
        raise ValidationError(f"{subject} marks must be a finite number.")
    if not 0 <= mark <= MAX_MARK:
        raise ValidationError(f"{subject} marks must be between 0 and 100.")
    return round(mark, 2)


def student_from_row(row: sqlite3.Row) -> Student:
    return Student(
        id=row["id"],
        name=row["name"],
        roll_number=row["roll_number"],
        class_name=row["class_name"],
        physics=float(row["physics"]),
        chemistry=float(row["chemistry"]),
        mathematics=float(row["mathematics"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class StudentService:
    """Business logic for student creation, updates, search, and reports."""

    def __init__(self, database: Database):
        self.db = database

    def add(
        self,
        name: str,
        roll_number: str,
        class_name: str,
        physics: object,
        chemistry: object,
        mathematics: object,
    ) -> Student:
        name = clean_text(name, "Name")
        roll_number = clean_text(roll_number, "Roll number", 40)
        class_name = clean_text(class_name, "Class", 80)
        marks = (
            validate_mark(physics, "Physics"),
            validate_mark(chemistry, "Chemistry"),
            validate_mark(mathematics, "Mathematics"),
        )
        timestamp = now()
        try:
            with self.db.connect() as con:
                cursor = con.execute("""
                    INSERT INTO students
                    (name, roll_number, class_name, physics, chemistry,
                     mathematics, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, roll_number, class_name, *marks, timestamp, timestamp))
                student_id = cursor.lastrowid
        except sqlite3.IntegrityError as exc:
            if "roll_number" in str(exc).lower():
                raise ValidationError(
                    f"Roll number '{roll_number}' already exists."
                ) from None
            raise
        self.db.audit("ADD", roll_number, f"Added student {name}")
        return self.get_by_id(int(student_id))

    def update(self, roll_number: str, **changes: object) -> Student:
        existing = self.get_by_roll(roll_number)
        allowed = {"name", "class_name", "physics", "chemistry", "mathematics"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValidationError(f"Unsupported fields: {', '.join(sorted(unknown))}")

        values = {
            "name": existing.name,
            "class_name": existing.class_name,
            "physics": existing.physics,
            "chemistry": existing.chemistry,
            "mathematics": existing.mathematics,
        }
        for key, value in changes.items():
            if key in ("name", "class_name"):
                values[key] = clean_text(value, key.replace("_", " ").title())
            else:
                subject = key.replace("_", " ").title()
                values[key] = validate_mark(value, subject)

        timestamp = now()
        with self.db.connect() as con:
            con.execute("""
                UPDATE students
                SET name=?, class_name=?, physics=?, chemistry=?, mathematics=?,
                    updated_at=?
                WHERE roll_number=? COLLATE NOCASE
            """, (
                values["name"], values["class_name"], values["physics"],
                values["chemistry"], values["mathematics"], timestamp,
                existing.roll_number,
            ))
        self.db.audit("UPDATE", existing.roll_number, f"Updated fields: {', '.join(changes)}")
        return self.get_by_roll(existing.roll_number)

    def delete(self, roll_number: str) -> None:
        student = self.get_by_roll(roll_number)
        with self.db.connect() as con:
            con.execute("DELETE FROM students WHERE id=?", (student.id,))
        self.db.audit("DELETE", student.roll_number, f"Deleted student {student.name}")

    def get_by_id(self, student_id: int) -> Student:
        with self.db.connect() as con:
            row = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        if row is None:
            raise StudentNotFoundError(f"No student with ID {student_id}.")
        return student_from_row(row)

    def get_by_roll(self, roll_number: str) -> Student:
        with self.db.connect() as con:
            row = con.execute(
                "SELECT * FROM students WHERE roll_number=? COLLATE NOCASE",
                (roll_number.strip(),),
            ).fetchone()
        if row is None:
            raise StudentNotFoundError(f"No student with roll number '{roll_number}'.")
        return student_from_row(row)

    def list_students(
        self, search: str = "", class_name: str = "", sort_by: str = "name"
    ) -> list[Student]:
        sort_columns = {
            "name": "name COLLATE NOCASE",
            "roll": "roll_number COLLATE NOCASE",
            "percentage": "(physics + chemistry + mathematics) / 3.0",
            "total": "(physics + chemistry + mathematics)",
        }
        order = sort_columns.get(sort_by, sort_columns["name"])
        sql = "SELECT * FROM students WHERE 1=1"
        params: list[object] = []
        if search.strip():
            pattern = f"%{search.strip()}%"
            sql += " AND (name LIKE ? OR roll_number LIKE ?)"
            params.extend([pattern, pattern])
        if class_name.strip():
            sql += " AND class_name LIKE ?"
            params.append(f"%{class_name.strip()}%")
        sql += f" ORDER BY {order}, roll_number COLLATE NOCASE"
        with self.db.connect() as con:
            rows = con.execute(sql, params).fetchall()
        return [student_from_row(row) for row in rows]

    def rankings(self, class_name: str = "") -> list[tuple[int, Student]]:
        students = self.list_students(class_name=class_name, sort_by="total")
        students.sort(key=lambda s: (s.total, s.percentage, s.name.lower()), reverse=True)
        return [(rank, student) for rank, student in enumerate(students, start=1)]

    def statistics(self, class_name: str = "") -> dict[str, float | int | None]:
        students = self.list_students(class_name=class_name)
        if not students:
            return {
                "count": 0, "average": None, "highest": None,
                "lowest": None, "pass_count": 0, "fail_count": 0,
                "pass_rate": None,
            }
        percentages = [s.percentage for s in students]
        pass_count = sum(s.result == "PASS" for s in students)
        return {
            "count": len(students),
            "average": sum(percentages) / len(percentages),
            "highest": max(percentages),
            "lowest": min(percentages),
            "pass_count": pass_count,
            "fail_count": len(students) - pass_count,
            "pass_rate": pass_count / len(students) * 100,
        }

    def export_csv(self, path: Path, class_name: str = "") -> int:
        students = self.list_students(class_name=class_name)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=[
                "name", "roll_number", "class_name", "physics",
                "chemistry", "mathematics",
            ])
            writer.writeheader()
            for s in students:
                writer.writerow({
                    "name": s.name, "roll_number": s.roll_number,
                    "class_name": s.class_name, "physics": s.physics,
                    "chemistry": s.chemistry, "mathematics": s.mathematics,
                })
        self.db.audit("EXPORT_CSV", None, f"Exported {len(students)} records to {path}")
        return len(students)

    def import_csv(self, path: Path) -> tuple[int, list[str]]:
        imported = 0
        errors: list[str] = []
        with path.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            required = {
                "name", "roll_number", "class_name", "physics",
                "chemistry", "mathematics",
            }
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValidationError(
                    "CSV needs columns: " + ", ".join(sorted(required))
                )
            for line_number, row in enumerate(reader, start=2):
                try:
                    self.add(
                        row["name"], row["roll_number"], row["class_name"],
                        row["physics"], row["chemistry"], row["mathematics"],
                    )
                    imported += 1
                except (ValidationError, StudentNotFoundError) as exc:
                    errors.append(f"Line {line_number}: {exc}")
        self.db.audit("IMPORT_CSV", None, f"Imported {imported} records from {path}")
        return imported, errors

    def backup(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = BACKUP_DIR / f"students_{stamp}.db"
        shutil.copy2(self.db.path, target)
        self.db.audit("BACKUP", None, f"Database backup created at {target}")
        return target

    def audit_history(self, limit: int = 20) -> list[sqlite3.Row]:
        with self.db.connect() as con:
            return con.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()


def line(char: str = "-", width: int = 100) -> str:
    return char * width


def moneyless_number(value: float | int | None, suffix: str = "") -> str:
    return "N/A" if value is None else f"{value:.2f}{suffix}"


def print_student(student: Student) -> None:
    print(line())
    print(f"ID: {student.id} | Roll: {student.roll_number} | Name: {student.name}")
    print(f"Class: {student.class_name}")
    print(
        f"Physics: {student.physics:g} | Chemistry: {student.chemistry:g} | "
        f"Mathematics: {student.mathematics:g}"
    )
    print(
        f"Total: {student.total:g}/300 | Percentage: {student.percentage:.2f}% | "
        f"Grade: {student.grade} | Result: {student.result}"
    )
    print(line())


def print_table(students: Iterable[Student]) -> None:
    items = list(students)
    if not items:
        print("\nNo student records found.")
        return
    headers = ("ROLL", "NAME", "CLASS", "TOTAL", "PERCENT", "GRADE", "RESULT")
    rows = [
        (
            s.roll_number[:14], s.name[:22], s.class_name[:15],
            f"{s.total:.1f}/300", f"{s.percentage:.2f}%", s.grade, s.result,
        )
        for s in items
    ]
    widths = [14, 22, 15, 10, 10, 7, 7]
    fmt = " | ".join(f"{{:<{w}}}" for w in widths)
    print("\n" + fmt.format(*headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*row))
    print(f"\nRecords: {len(items)}")


def prompt(prompt_text: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default is not None else ""
    value = input(f"{prompt_text}{suffix}: ").strip()
    return value if value else (default or "")


def prompt_mark(subject: str, default: float | None = None) -> float:
    while True:
        raw = prompt(f"{subject} marks (0-100)", str(default) if default is not None else None)
        try:
            return validate_mark(raw, subject)
        except ValidationError as exc:
            print(f"Error: {exc}")


def prompt_nonempty(label: str, default: str | None = None) -> str:
    while True:
        value = prompt(label, default)
        try:
            return clean_text(value, label)
        except ValidationError as exc:
            print(f"Error: {exc}")


def confirm(message: str) -> bool:
    return prompt(f"{message} (y/N)").lower() in {"y", "yes"}


def add_student_ui(service: StudentService) -> None:
    print("\nADD STUDENT")
    name = prompt_nonempty("Student name")
    roll = prompt_nonempty("Unique roll number")
    class_name = prompt_nonempty("Class", "First Year")
    physics = prompt_mark("Physics")
    chemistry = prompt_mark("Chemistry")
    mathematics = prompt_mark("Mathematics")
    student = service.add(name, roll, class_name, physics, chemistry, mathematics)
    print("\nStudent added successfully.")
    print_student(student)


def view_students_ui(service: StudentService) -> None:
    search = prompt("Search by name or roll number (blank for all)")
    class_name = prompt("Filter by class (blank for all)")
    sort_by = prompt("Sort by: name / roll / total / percentage", "name").lower()
    students = service.list_students(search, class_name, sort_by)
    print_table(students)


def search_student_ui(service: StudentService) -> None:
    query = prompt_nonempty("Enter roll number")
    try:
        print_student(service.get_by_roll(query))
    except StudentNotFoundError as exc:
        print(f"Not found: {exc}")


def update_student_ui(service: StudentService) -> None:
    roll = prompt_nonempty("Roll number to update")
    try:
        student = service.get_by_roll(roll)
    except StudentNotFoundError as exc:
        print(exc)
        return
    print_student(student)
    print("Leave a field blank to keep its current value.")
    changes: dict[str, object] = {}
    name = prompt("New name", student.name)
    class_name = prompt("New class", student.class_name)
    if name != student.name:
        changes["name"] = name
    if class_name != student.class_name:
        changes["class_name"] = class_name
    for key, label, current in (
        ("physics", "Physics", student.physics),
        ("chemistry", "Chemistry", student.chemistry),
        ("mathematics", "Mathematics", student.mathematics),
    ):
        raw = input(f"New {label} marks [{current:g}] (blank to keep): ").strip()
        if raw:
            changes[key] = validate_mark(raw, label)
    if not changes:
        print("No changes made.")
        return
    updated = service.update(roll, **changes)
    print("Student updated.")
    print_student(updated)


def delete_student_ui(service: StudentService) -> None:
    roll = prompt_nonempty("Roll number to delete")
    try:
        student = service.get_by_roll(roll)
    except StudentNotFoundError as exc:
        print(exc)
        return
    print_student(student)
    if confirm("Permanently delete this student?"):
        service.delete(roll)
        print("Student deleted.")
    else:
        print("Deletion cancelled.")


def rankings_ui(service: StudentService) -> None:
    class_name = prompt("Class filter (blank for all)")
    ranked = service.rankings(class_name)
    if not ranked:
        print("No records to rank.")
        return
    print("\nCLASS RANKING")
    print(line("="))
    for rank, student in ranked:
        print(
            f"{rank:>3}. {student.name:<25} ({student.roll_number:<12}) "
            f"{student.percentage:6.2f}% | {student.grade:>2} | {student.result}"
        )


def statistics_ui(service: StudentService) -> None:
    stats = service.statistics(prompt("Class filter (blank for all)"))
    print("\nCLASS STATISTICS")
    print(line("="))
    print(f"Students:       {stats['count']}")
    print(f"Average:        {moneyless_number(stats['average'], '%')}")
    print(f"Highest:        {moneyless_number(stats['highest'], '%')}")
    print(f"Lowest:         {moneyless_number(stats['lowest'], '%')}")
    print(f"Passed:         {stats['pass_count']}")
    print(f"Failed:         {stats['fail_count']}")
    print(f"Pass rate:      {moneyless_number(stats['pass_rate'], '%')}")


def export_ui(service: StudentService) -> None:
    default = ROOT_DIR / "students_export.csv"
    target_text = prompt("Export path", str(default))
    target = Path(target_text).expanduser()
    count = service.export_csv(target)
    print(f"Exported {count} records to {target.resolve()}")


def import_ui(service: StudentService) -> None:
    target = Path(prompt_nonempty("CSV file path")).expanduser()
    if not target.is_file():
        print("File does not exist.")
        return
    try:
        count, errors = service.import_csv(target)
    except (OSError, ValidationError) as exc:
        print(f"Import failed: {exc}")
        return
    print(f"Imported {count} records.")
    if errors:
        print(f"{len(errors)} row(s) skipped:")
        for error in errors[:20]:
            print(f"  - {error}")
        if len(errors) > 20:
            print(f"  ... and {len(errors) - 20} more.")


def backup_ui(service: StudentService) -> None:
    try:
        path = service.backup()
        print(f"Backup created: {path}")
    except OSError as exc:
        print(f"Backup failed: {exc}")


def audit_ui(service: StudentService) -> None:
    rows = service.audit_history()
    if not rows:
        print("No activity has been recorded yet.")
        return
    print("\nRECENT ACTIVITY")
    print(line("="))
    for row in rows:
        print(
            f"{row['timestamp']} | {row['action']:<12} | "
            f"{row['student_roll'] or '-':<14} | {row['details']}"
        )


def print_banner() -> None:
    print(r"""
  _____ _             _            _     ____            _       _
 / ____| |           | |          | |   |  _ \          | |     | |
| (___ | |_ _   _  __| | ___ _ __ | |_  | |_) | ___  ___| |_   _| |_
 \___ \| __| | | |/ _` |/ _ \ '_ \| __| |  _ < / _ \/ __| | | | | __|
 ____) | |_| |_| | (_| |  __/ | | | |_  | |_) |  __/ (__| | |_| | |_
|_____/ \__|\__,_|\__,_|\___|_| |_|\__| |____/ \___|\___|_|\__,_|\__|

                    Student Result Manager v2.0
    """)
    print("A local student records app • SQLite database • CSV tools • reports\n")


MENU = {
    "1": ("Add student", add_student_ui),
    "2": ("View / filter students", view_students_ui),
    "3": ("Search student", search_student_ui),
    "4": ("Update student", update_student_ui),
    "5": ("Delete student", delete_student_ui),
    "6": ("Class rankings", rankings_ui),
    "7": ("Class statistics", statistics_ui),
    "8": ("Export records to CSV", export_ui),
    "9": ("Import records from CSV", import_ui),
    "10": ("Back up database", backup_ui),
    "11": ("Recent activity log", audit_ui),
}


def main() -> int:
    print_banner()
    try:
        service = StudentService(Database())
    except (OSError, sqlite3.Error) as exc:
        print(f"Could not initialize the database: {exc}")
        logger.exception("Database initialization failed")
        return 1

    while True:
        print("\n" + line("="))
        for key, (label, _) in MENU.items():
            print(f"{key:>2}. {label}")
        print(" 0. Exit")
        print(line("="))
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye! Your records are stored locally.")
            return 0
        action = MENU.get(choice)
        if action is None:
            print("Invalid choice. Enter a number shown in the menu.")
            continue
        try:
            action[1](service)
        except (ValidationError, StudentNotFoundError) as exc:
            print(f"Error: {exc}")
            logger.warning("%s", exc)
        except (OSError, sqlite3.Error) as exc:
            print(f"Operation failed: {exc}")
            logger.exception("Operation failed")
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled.")
        except Exception:
            logger.exception("Unexpected error")
            print("An unexpected error occurred. Check data/app.log for details.")


if __name__ == "__main__":
    raise SystemExit(main())
