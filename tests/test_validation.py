"""Adversarial validation cases; run with python -m unittest discover -s tests -v."""

import copy
import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from uuid import UUID

from src.validation import SPECS, validate_directory


P = "aaaaaaaa-1111-2222-3333-444444444444"
O = "bbbbbbbb-1111-2222-3333-444444444444"
E = "cccccccc-1111-2222-3333-444444444444"
BASE = {
    "patients": [{"Id": P, "BIRTHDATE": "1980-01-01", "DEATHDATE": "", "GENDER": "F"}],
    "organizations": [{"Id": O, "NAME": "Sample Hospital", "CITY": "Boston", "STATE": "MA"}],
    "encounters": [{
        "Id": E, "PATIENT": P, "ORGANIZATION": O,
        "START": "2020-01-02T12:00:00Z", "STOP": "2020-01-02T13:00:00Z",
        "ENCOUNTERCLASS": "ambulatory", "BASE_ENCOUNTER_COST": "13.70",
    }],
}


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name)
        self.rows = copy.deepcopy(BASE)

    def tearDown(self):
        self.temporary.cleanup()

    def validate(self):
        for name, rows in self.rows.items():
            with (self.directory / f"{name}.csv").open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(SPECS[name]))
                writer.writeheader()
                writer.writerows(rows)
        return validate_directory(self.directory)

    def test_valid_values_are_typed_and_optional_null_is_preserved(self):
        self.rows["encounters"][0]["STOP"] = ""
        self.rows["organizations"][0]["STATE"] = ""
        tables, report = self.validate()
        patient = tables["patients"][0]
        encounter = tables["encounters"][0]
        self.assertIsInstance(patient["patient_id"], UUID)
        self.assertIsInstance(patient["birth_date"], date)
        self.assertIsNone(patient["death_date"])
        self.assertIsInstance(encounter["start_time"], datetime)
        self.assertIsNotNone(encounter["start_time"].utcoffset())
        self.assertEqual(encounter["base_encounter_cost"], Decimal("13.70"))
        self.assertIsNone(encounter["stop_time"])
        self.assertEqual(report["tables"]["encounters"]["expected_nulls"], {"stop_time": 1})
        self.assertEqual(report["tables"]["encounters"]["corrected_rows"], 0)

    def test_malformed_identifier_rejects_record(self):
        self.rows["encounters"][0]["Id"] = "not-a-uuid"
        tables, report = self.validate()
        self.assertEqual(tables["encounters"], [])
        self.assertIn("encounter_id:invalid_uuid", report["rejected"][0]["reasons"])

    def test_rejected_parent_rejects_referencing_child(self):
        self.rows["patients"][0]["BIRTHDATE"] = "1980-02-30"
        tables, report = self.validate()
        self.assertEqual(tables["patients"], [])
        self.assertEqual(tables["encounters"], [])
        self.assertEqual(report["tables"]["encounters"]["rejection_reasons"],
                         {"patient_reference_missing_or_rejected": 1})

    def test_missing_parent_reference_is_rejected(self):
        self.rows["encounters"][0]["ORGANIZATION"] = "dddddddd-1111-2222-3333-444444444444"
        _, report = self.validate()
        self.assertEqual(report["tables"]["encounters"]["rejected_rows"], 1)
        self.assertIn("organization_reference_missing_or_rejected", report["rejected"][0]["reasons"])

    def test_timezone_is_required_and_offsets_are_normalized(self):
        self.rows["encounters"][0]["START"] = "2020-01-02T12:00:00"
        _, report = self.validate()
        self.assertEqual(report["tables"]["encounters"]["accepted_rows"], 0)
        self.rows["encounters"][0]["START"] = "2020-01-02T07:00:00-05:00"
        tables, _ = self.validate()
        self.assertEqual(tables["encounters"][0]["start_time"].isoformat(), "2020-01-02T12:00:00+00:00")

    def test_malformed_offset_cannot_be_silently_normalized(self):
        for offset in ("+00:99", "-01:60", "+24:00"):
            with self.subTest(offset=offset):
                self.rows["encounters"][0]["START"] = "2020-01-02T12:00:00" + offset
                tables, report = self.validate()
                self.assertEqual(tables["encounters"], [])
                self.assertIn("start_time:invalid_or_timezone_missing_timestamp",
                              report["rejected"][0]["reasons"])

    def test_nul_in_text_is_rejected_instead_of_truncated_by_parser(self):
        self.rows["organizations"][0]["NAME"] = "Hospital\x00hidden suffix"
        tables, report = self.validate()
        self.assertEqual(tables["organizations"], [])
        self.assertEqual(tables["encounters"], [])
        self.assertIn("name:nul_character", report["rejected"][0]["reasons"])

    def test_invalid_decimal_values_are_never_rounded_or_loaded(self):
        for value in ("1.234", "NaN", "Infinity", "-0.01", "1000000000000.00", "1e2"):
            with self.subTest(value=value):
                self.rows["encounters"][0]["BASE_ENCOUNTER_COST"] = value
                tables, report = self.validate()
                self.assertEqual(tables["encounters"], [])
                self.assertEqual(report["tables"]["encounters"]["rejected_rows"], 1)

    def test_identical_duplicate_has_deterministic_first_winner(self):
        self.rows["encounters"].append(copy.deepcopy(self.rows["encounters"][0]))
        tables, report = self.validate()
        self.assertEqual(len(tables["encounters"]), 1)
        self.assertEqual(report["rejected"][0]["source_row"], 3)
        self.assertEqual(report["rejected"][0]["reasons"], ["identical_duplicate_id"])

    def test_conflicting_duplicates_reject_every_instance(self):
        duplicate = copy.deepcopy(self.rows["encounters"][0])
        duplicate["BASE_ENCOUNTER_COST"] = "99.00"
        self.rows["encounters"].append(duplicate)
        tables, report = self.validate()
        self.assertEqual(tables["encounters"], [])
        self.assertEqual(report["tables"]["encounters"]["rejected_rows"], 2)
        self.assertTrue(all("conflicting_duplicate_id" in row["reasons"] for row in report["rejected"]))

    def test_invalid_duplicate_cannot_leave_an_arbitrary_valid_winner(self):
        duplicate = copy.deepcopy(self.rows["patients"][0])
        duplicate["BIRTHDATE"] = "not-a-date"
        self.rows["patients"].append(duplicate)
        tables, report = self.validate()
        self.assertEqual(tables["patients"], [])
        self.assertEqual(tables["encounters"], [])
        self.assertEqual(report["tables"]["patients"]["rejected_rows"], 2)

    def test_corrections_are_counted_by_row_cell_and_reason(self):
        self.rows["patients"][0]["Id"] = " " + P.upper() + " "
        self.rows["encounters"][0]["ENCOUNTERCLASS"] = " Ambulatory "
        tables, report = self.validate()
        self.assertEqual(len(tables["encounters"]), 1)
        self.assertEqual(report["tables"]["patients"]["corrected_rows"], 1)
        self.assertEqual(report["tables"]["patients"]["correction_cells"], 1)
        self.assertEqual(report["tables"]["patients"]["correction_reasons"],
                         {"trim_whitespace": 1, "canonical_uuid": 1})
        self.assertEqual(report["tables"]["encounters"]["correction_cells"], 1)
        self.assertEqual(tables["encounters"][0]["encounter_class"], "ambulatory")

    def test_stop_before_start_is_rejected_but_equal_is_valid(self):
        self.rows["encounters"][0]["STOP"] = "2020-01-02T11:00:00Z"
        tables, report = self.validate()
        self.assertEqual(tables["encounters"], [])
        self.assertIn("stop_before_start", report["rejected"][0]["reasons"])
        self.rows["encounters"][0]["STOP"] = self.rows["encounters"][0]["START"]
        tables, _ = self.validate()
        self.assertEqual(len(tables["encounters"]), 1)

    def test_before_birth_is_rejected_post_death_is_retained_with_warning(self):
        self.rows["patients"][0]["BIRTHDATE"] = "2021-01-01"
        tables, report = self.validate()
        self.assertEqual(tables["encounters"], [])
        self.assertIn("encounter_before_birth", report["rejected"][0]["reasons"])
        self.rows["patients"][0]["BIRTHDATE"] = "1980-01-01"
        self.rows["patients"][0]["DEATHDATE"] = "2020-01-01"
        tables, report = self.validate()
        self.assertEqual(len(tables["encounters"]), 1)
        self.assertEqual(report["warning_counts"], {"encounter_after_death_retained": 1})

    def test_same_day_death_does_not_imply_a_known_time_of_death(self):
        self.rows["patients"][0]["DEATHDATE"] = "2020-01-02"
        tables, report = self.validate()
        self.assertEqual(len(tables["encounters"]), 1)
        self.assertEqual(report["warnings"], [])

    def test_open_class_vocabulary_and_gender_are_preserved(self):
        self.rows["patients"][0]["GENDER"] = "X"
        self.rows["encounters"][0]["ENCOUNTERCLASS"] = "new_class"
        tables, _ = self.validate()
        self.assertEqual(tables["patients"][0]["gender"], "X")
        self.assertEqual(tables["encounters"][0]["encounter_class"], "new_class")

    def test_required_blank_is_rejected_and_na_is_literal_text(self):
        self.rows["organizations"][0]["NAME"] = "  "
        tables, report = self.validate()
        self.assertEqual(tables["organizations"], [])
        self.assertIn("name:missing_required", report["rejected"][0]["reasons"])
        self.rows["organizations"][0]["NAME"] = "NA"
        tables, _ = self.validate()
        self.assertEqual(tables["organizations"][0]["name"], "NA")

    def test_malformed_csv_structure_fails_before_validation(self):
        self.validate()
        with (self.directory / "patients.csv").open("a", encoding="utf-8") as stream:
            stream.write("too,few,fields\n")
        with self.assertRaisesRegex(ValueError, "wrong field count"):
            validate_directory(self.directory)


if __name__ == "__main__":
    unittest.main()
