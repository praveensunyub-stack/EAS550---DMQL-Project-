"""The rows from the source data, the relationships between tables, the data quality, and if we obtain consistent results when loading the data back again."""
import argparse
from collections import Counter
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from .db import get_engine
from .validation import validate_directory

TABLES = {
    "patients": ("patient_id", "birth_date", "death_date", "gender"),
    "organizations": ("organization_id", "name", "city", "state"),
    "encounters": ("encounter_id", "patient_id", "organization_id", "start_time",
                   "stop_time", "encounter_class", "base_encounter_cost"),
}


def canonical(value):
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value.quantize(Decimal("0.01")), "f")
    if isinstance(value, UUID):
        return str(value)
    return value


def table_fingerprint(rows, columns):
    """Hash is created for all the chosen values, while retaining the order of the columns and primary keys intact."""
    ordered = sorted(rows, key=lambda row: str(row[columns[0]]))
    content = [[canonical(row[col]) for col in columns] for row in ordered]
    keys = [row[0] for row in content]

    def digest(value):
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    return {"row_count": len(content), "duplicate_key_rows": len(keys) - len(set(keys)),
            "key_sha256": digest(keys), "content_sha256": digest(content)}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def verify(engine, report_path=None, data_dir=None):
    """The consistency of read-only snapshot is used to test the database and generate a report that tells us if all tests were successful."""
    with engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        with connection.begin():
            connection.execute(text("SET TRANSACTION READ ONLY"))
            connection.execute(text("SET LOCAL TIME ZONE 'UTC'"))
            rows = {
                name: [dict(row) for row in connection.execute(text(
                    f"SELECT {', '.join(columns)} FROM source.{name} ORDER BY {columns[0]}"
                )).mappings()]
                for name, columns in TABLES.items()
            }
            version = connection.execute(text("SHOW server_version")).scalar_one()
            relation_names = connection.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'source' ORDER BY tablename"
            )).scalars().all()
    patients = {row["patient_id"]: row for row in rows["patients"]}
    organizations = {row["organization_id"]: row for row in rows["organizations"]}
    encounters = rows["encounters"]
    before_birth, after_death = [], []
    for encounter in encounters:
        patient = patients.get(encounter["patient_id"])
        if patient is None:
            continue
        started = encounter["start_time"].astimezone(timezone.utc).date()
        if started < patient["birth_date"]:
            before_birth.append(str(encounter["encounter_id"]))
        if patient["death_date"] is not None and started > patient["death_date"]:
            after_death.append(str(encounter["encounter_id"]))
    checks = {
        "exactly_three_source_tables": relation_names == sorted(TABLES),
        "missing_patient_references": sum(row["patient_id"] not in patients for row in encounters),
        "missing_organization_references": sum(row["organization_id"] not in organizations for row in encounters),
        "stop_before_start": sum(row["stop_time"] is not None and row["stop_time"] < row["start_time"] for row in encounters),
        "death_before_birth": sum(row["death_date"] is not None and row["death_date"] < row["birth_date"] for row in patients.values()),
        "invalid_costs": sum(not row["base_encounter_cost"].is_finite() or row["base_encounter_cost"] < 0 for row in encounters),
        "encounters_before_birth": len(before_birth),
    }
    fingerprints = {name: table_fingerprint(rows[name], columns) for name, columns in TABLES.items()}
    source_match = None
    if data_dir is not None:
        expected, _ = validate_directory(Path(data_dir))
        source_match = {
            name: table_fingerprint(expected[name], columns) == fingerprints[name]
            for name, columns in TABLES.items()
        }
    total_cost = sum((row["base_encounter_cost"] for row in encounters), Decimal("0.00"))
    deltas = [row["stop_time"] - row["start_time"] for row in encounters if row["stop_time"] is not None]
    durations = [Decimal(delta.days * 86400 + delta.seconds) + Decimal(delta.microseconds) / Decimal(1000000)
                 for delta in deltas]
    measures = {
        "total_base_encounter_cost": format(total_cost, ".2f"),
        "total_completed_duration_seconds": format(sum(durations, Decimal("0")), "f"),
        "null_stop_count": sum(row["stop_time"] is None for row in encounters),
        "null_death_count": sum(row["death_date"] is None for row in patients.values()),
        "encounters_by_class": dict(sorted(Counter(row["encounter_class"] for row in encounters).items())),
        "referenced_patient_count": len({row["patient_id"] for row in encounters}),
        "referenced_organization_count": len({row["organization_id"] for row in encounters}),
    }
    passed = (checks["exactly_three_source_tables"] and
              all(value == 0 for key, value in checks.items() if key != "exactly_three_source_tables") and
              all(fp["row_count"] > 0 and fp["duplicate_key_rows"] == 0 for fp in fingerprints.values()) and
              (source_match is None or all(source_match.values())))
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "postgresql_version": version,
        "passed": passed,
        "tables": fingerprints,
        "checks": checks,
        "measures": measures,
        "source_matches_database": source_match,
        "warnings": {"encounters_after_death": len(after_death), "encounter_ids": sorted(after_death),
                     "policy": "Retain source values; report chronology anomalies without inventing corrections."},
    }
    if report_path is not None:
        write_json(report_path, report)
    return report


def compare_reports(first, second):
    """Comparison is made between the obtained values and theoretical values without the particulars that vary each time."""
    fields = ("tables", "checks", "measures", "source_matches_database", "warnings")
    comparisons = {field: first[field] == second[field] for field in fields}
    return {"passed": first["passed"] and second["passed"] and all(comparisons.values()),
            "equal": comparisons,
            "method": "Sorted full-row SHA-256 plus sorted key SHA-256, exact cost/duration totals, classes and quality checks."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--compare", type=Path)
    args = parser.parse_args()
    if args.compare and args.report.resolve() == args.compare.resolve():
        parser.error("--report and --compare must be different files.")
    engine = get_engine()
    try:
        report = verify(engine, args.report, args.data_dir)
        passed = report["passed"]
        if args.compare:
            comparison = compare_reports(json.loads(args.compare.read_text(encoding="utf-8")), report)
            print(json.dumps(comparison, indent=2))
            passed = passed and comparison["passed"]
        print(json.dumps({"passed": passed, "row_counts": {k: v["row_count"] for k, v in report["tables"].items()}}, indent=2))
        if not passed:
            raise SystemExit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
