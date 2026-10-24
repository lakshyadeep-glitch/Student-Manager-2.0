import tempfile
import unittest
from pathlib import Path

from student_result_manager import (
    Database,
    StudentService,
    ValidationError,
    StudentNotFoundError,
    validate_mark,
)


class StudentResultManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_students.db"
        self.service = StudentService(Database(self.db_path))

    def tearDown(self):
        self.temp_dir.cleanup()

    def add_sample(self, roll="CSE001", physics=80, chemistry=90, mathematics=70):
        return self.service.add(
            "Aarav Sharma", roll, "First Year", physics, chemistry, mathematics
        )

    def test_add_and_calculate_percentage(self):
        student = self.add_sample()
        self.assertEqual(student.total, 240)
        self.assertAlmostEqual(student.percentage, 80)
        self.assertEqual(student.grade, "A")
        self.assertEqual(student.result, "PASS")

    def test_marks_out_of_range_are_rejected(self):
        with self.assertRaises(ValidationError):
            validate_mark(101, "Physics")
        with self.assertRaises(ValidationError):
            validate_mark(-1, "Physics")

    def test_non_numeric_marks_are_rejected(self):
        with self.assertRaises(ValidationError):
            validate_mark("excellent", "Physics")

    def test_duplicate_roll_is_rejected(self):
        self.add_sample()
        with self.assertRaises(ValidationError):
            self.add_sample()

    def test_failed_subject_means_fail(self):
        student = self.add_sample(physics=32)
        self.assertEqual(student.result, "FAIL")
        self.assertEqual(student.grade, "F")

    def test_update_student(self):
        self.add_sample()
        updated = self.service.update("CSE001", physics=99, name="Aarav S.")
        self.assertEqual(updated.physics, 99)
        self.assertEqual(updated.name, "Aarav S.")

    def test_delete_student(self):
        self.add_sample()
        self.service.delete("CSE001")
        with self.assertRaises(StudentNotFoundError):
            self.service.get_by_roll("CSE001")

    def test_search_by_name(self):
        self.add_sample()
        results = self.service.list_students(search="Aarav")
        self.assertEqual(len(results), 1)

    def test_statistics_empty_database(self):
        stats = self.service.statistics()
        self.assertEqual(stats["count"], 0)
        self.assertIsNone(stats["average"])


if __name__ == "__main__":
    unittest.main()
