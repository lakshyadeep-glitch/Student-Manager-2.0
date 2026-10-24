# Student Result Manager

A feature-rich, beginner-friendly command-line application for managing student marks and academic results. Built with Python and SQLite, using only the Python standard library.

```text
  _____ _             _            _     ____            _       _
 / ____| |           | |          | |   |  _ \          | |     | |
| (___ | |_ _   _  __| | ___ _ __ | |_  | |_) | ___  ___| |_   _| |_
 \___ \| __| | | |/ _` |/ _ \ '_ \| __| |  _ < / _ \/ __| | | | | __|
 ____) | |_| |_| | (_| |  __/ | | | |_  | |_) |  __/ (__| | |_| | |_
|_____/ \__|\__,_|\__,_|\___|_| |_|\__| |____/ \___|\___|_|\__,_|\__|

              +----------------------------------+
              |       STUDENT RESULT MANAGER     |
              +----------------------------------+
              |  [1] Add       [2] View          |
              |  [3] Search    [4] Update         |
              |  [5] Delete    [6] Rankings       |
              |  [7] Statistics [8] Export CSV    |
              |  [9] Import CSV [10] Backup       |
              |  [11] Activity Log [0] Exit       |
              +----------------------------------+
```

## Features

- **Create student records** with a unique roll number, name, class, and three subject marks.
- **Read and search records** by student name or roll number.
- **Update records** without re-entering every field.
- **Delete records** after confirmation.
- **Calculate results**: total, percentage, grade, and pass/fail status.
- **Rank students** by total marks.
- **View class statistics**: average, highest and lowest percentage, pass count, fail count, and pass rate.
- **Import and export CSV** for spreadsheet workflows.
- **Automatic local persistence** using SQLite.
- **Database backups** saved in `data/backups/`.
- **Activity log** for additions, edits, deletions, imports, exports, and backups.
- **Input validation** for required text fields and marks from 0 to 100.
- **No third-party packages required**.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux
- SQLite support (included with most standard Python installations)

## Run it

1. Download or clone this project.
2. Open a terminal in the project directory.
3. Run:

   ```bash
   python student_result_manager.py
   ```

   On some Linux installations, use `python3 student_result_manager.py`.

The application creates `data/students.db` automatically on first launch. Records remain available after closing the program.

## Menu

| Option | Action |
|---:|---|
| 1 | Add student |
| 2 | View and filter students |
| 3 | Search for a student by roll number |
| 4 | Update student details or marks |
| 5 | Delete a student |
| 6 | Display class rankings |
| 7 | Display class statistics |
| 8 | Export records to CSV |
| 9 | Import records from CSV |
| 10 | Create a database backup |
| 11 | View recent activity |
| 0 | Exit |

## Grade rules

The current grading policy is deliberately simple and is defined in the `Student.grade` property:

| Rule | Grade |
|---|---|
| Any subject below 33 | F |
| 90% and above, with every subject passed | A+ |
| 80–89.99% | A |
| 70–79.99% | B |
| 60–69.99% | C |
| 50–59.99% | D |
| Below 50%, with every subject passed | E |

A student passes only when each of the three subjects has at least 33 marks. Change `PASS_MARK` or the grade thresholds if your institution uses a different policy.

## CSV format

CSV imports must contain these column names:

```csv
name,roll_number,class_name,physics,chemistry,mathematics
Aarav Sharma,CSE001,First Year,88,91,84
Mira Das,CSE002,First Year,76,82,89
```

Roll numbers must be unique. Invalid rows are skipped and reported, while valid rows are imported. Exporting creates a CSV that can be opened in Excel, LibreOffice Calc, or Google Sheets.

## Project structure

```text
student-result-manager/
├── student_result_manager.py   # Application and business logic
├── README.md                   # Documentation
├── requirements.txt            # No external dependencies
├── .gitignore                  # Keeps generated data out of Git
├── data/
│   └── .gitkeep                # Database/logs/backups are created here
└── tests/
    └── test_student_result_manager.py
```

## Data and privacy

All records are stored locally in `data/students.db`. The application does not send records to a server. Keep backups somewhere safe, and do not commit real student records, logs, or database backups to a public repository.

## Tests

Run the unit tests with:

```bash
python -m unittest discover -s tests -v
```

The tests use temporary databases and do not modify your real application database.

## Known limitations

- The app is a local terminal program, not a multi-user web service.
- It currently manages Physics, Chemistry, and Mathematics only.
- The grading policy is an example; verify it against your institution's rules.
- CSV import uses the exact column names documented above.
- This project is intended as an educational portfolio project, not an officially certified school records system.

## Learning goals

This project demonstrates Python functions, classes, dataclasses, exceptions, type hints, SQLite, SQL constraints, CSV files, logging, filesystem operations, unit tests, and separation between data access and user interaction.

## Possible future improvements

- Configurable subjects and grading policies
- GUI using Tkinter or a web interface using Flask
- User login and role-based permissions
- PDF report cards
- Charts for class performance
- More advanced database migrations
- Automated backups and restore workflow
- Accessibility and localization improvements

 _        _    _   _  ____  _  _  __   __   _
| |      / \  | | | |/ ___|| || | \ \ / /  / \
| |     / _ \ | |_| |\___ \| || |_ \ V /  / _ \
| |___ / ___ \|  _  | ___) |__   _| | |  / ___ \
|_____/_/   \_\_| |_||____/   |_|   |_| /_/   \_\

                    by Lakshya
