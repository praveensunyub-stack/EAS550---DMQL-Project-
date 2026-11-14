"""Look at the chosen Synthea CSV data before importing it into the database.

Rows begin from 1, and include the header row as well. 
We are using the selected fields only, so such information as SSN and passport will not be included in our tables."""

from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import csv
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID

import pandas as pd


SPECS = {
    "patients": {
        "Id": ("patient_id", "uuid", False),
        "BIRTHDATE": ("birth_date", "date", False),
        "DEATHDATE": ("death_date", "date", True),
        "GENDER": ("gender", "text", False),
    },
    "organizations": {
        "Id": ("organization_id", "uuid", False),
        "NAME": ("name", "text", False),
        "CITY": ("city", "text", False),
        "STATE": ("state", "text", True),
    },
    "encounters": {
        "Id": ("encounter_id", "uuid", False),
        "PATIENT": ("patient_id", "uuid", False),
        "ORGANIZATION": ("organization_id", "uuid", False),
        "START": ("start_time", "timestamp", False),
        "STOP": ("stop_time", "timestamp", True),
        "ENCOUNTERCLASS": ("encounter_class", "class", False),
        "BASE_ENCOUNTER_COST": ("base_encounter_cost", "money", False),
    },
}
ID_COLUMNS = {name: next(iter(spec.values()))[0] for name, spec in SPECS.items()}
UUID_PATTERN = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z")
DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
TIMESTAMP_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z"
)
MONEY_PATTERN = re.compile(r"[+-]?\d+(?:\.\d{1,2})?\Z")
MAX_COST = Decimal("999999999999.99")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_manifest(data_dir, manifest_path):
    """Fail before loading when any selected CSV differs from the pinned input."""
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    for name in SPECS:
        filename = name + ".csv"
        expected = manifest["files"][filename]["sha256"]
        if sha256_file(Path(data_dir) / filename) != expected:
            raise ValueError(f"Checksum mismatch for {filename}; use the documented source snapshot")
    return manifest


def _parse(value, kind):
    if kind == "uuid":
        if not UUID_PATTERN.fullmatch(value):
            raise ValueError("invalid_uuid")
        return UUID(value)
    if kind == "date":
        if not DATE_PATTERN.fullmatch(value):
            raise ValueError("invalid_date")
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("invalid_date") from exc
    if kind == "timestamp":
        if not TIMESTAMP_PATTERN.fullmatch(value):
            raise ValueError("invalid_or_timezone_missing_timestamp")
        if not value.endswith("Z"):
            offset_hour, offset_minute = int(value[-5:-3]), int(value[-2:])
            if offset_hour > 23 or offset_minute > 59:
                # datetime.fromisoformat normalizes some malformed minute
                # offsets such as +00:99; reject them before conversion.
                raise ValueError("invalid_or_timezone_missing_timestamp")
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if result.tzinfo is None or result.utcoffset() is None:
                raise ValueError
            return result.astimezone(timezone.utc)
        except (ValueError, OverflowError) as exc:
            raise ValueError("invalid_or_timezone_missing_timestamp") from exc
    if kind == "money":
        if not MONEY_PATTERN.fullmatch(value):
            raise ValueError("invalid_money_or_precision")
        try:
            amount = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError("invalid_money_or_precision") from exc
        if not amount.is_finite() or amount < 0 or amount > MAX_COST:
            raise ValueError("money_out_of_range")
        return amount.quantize(Decimal("0.01"))
    if "\x00" in value:
        raise ValueError("nul_character")
    return value.lower() if kind == "class" else value


def _read_table(data_dir, name):
    path = Path(data_dir) / f"{name}.csv"
    spec = SPECS[name]
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        for record_number, fields in enumerate(reader, start=2):
            if len(fields) != len(header):
                raise ValueError(f"Malformed CSV record {record_number} in {name}: wrong field count")
    duplicates = [key for key, count in Counter(header).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate CSV columns in {name}: {', '.join(duplicates)}")
    missing = set(spec) - set(header)
    if missing:
        raise ValueError(f"Missing CSV columns in {name}: {', '.join(sorted(missing))}")
    # The Python parser preserves NUL characters so validation can reject them;
    # the C parser can silently truncate a field at a NUL byte.
    frame = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig", engine="python")
    records = []
    for index, raw in enumerate(frame.loc[:, list(spec)].to_dict(orient="records"), start=2):
        item = {"source_row": index, "data": {}, "reasons": [], "corrections": []}
        for csv_name, (column, kind, nullable) in spec.items():
            original = raw[csv_name]
            value = original.strip()
            if value != original:
                item["corrections"].append({"column": column, "reason": "trim_whitespace"})
            if not value:
                if nullable:
                    item["data"][column] = None
                else:
                    item["reasons"].append(f"{column}:missing_required")
                continue
            try:
                parsed = _parse(value, kind)
                item["data"][column] = parsed
                if kind == "uuid" and str(parsed) != value:
                    item["corrections"].append({"column": column, "reason": "canonical_uuid"})
                if kind == "class" and parsed != value:
                    item["corrections"].append({"column": column, "reason": "lowercase_class"})
            except ValueError as exc:
                item["reasons"].append(f"{column}:{exc}")
        data = item["data"]
        if name == "patients" and data.get("birth_date") and data.get("death_date"):
            if data["death_date"] < data["birth_date"]:
                item["reasons"].append("death_before_birth")
        if name == "encounters" and data.get("start_time") and data.get("stop_time"):
            if data["stop_time"] < data["start_time"]:
                item["reasons"].append("stop_before_start")
        records.append(item)

    # If an ID has any difference in data or an invalid row, 
    # then we will reject all the records associated with that ID.
    groups = defaultdict(list)
    for item in records:
        identifier = item["data"].get(ID_COLUMNS[name])
        if identifier is not None:
            groups[identifier].append(item)
    for group in groups.values():
        if len(group) < 2:
            continue
        if any(item["reasons"] for item in group) or any(
            item["data"] != group[0]["data"] for item in group[1:]
        ):
            for item in group:
                item["reasons"].append("conflicting_duplicate_id")
        else:
            for item in group[1:]:
                item["reasons"].append("identical_duplicate_id")
    return records


def validate_directory(data_dir):
    """Validate the three CSV tables and output the valid entries along with a report.

    In case there are any missing columns or the CSV files do not adhere to the proper format, 
    then the validation process is halted. Invalid entries are skipped and reported. 
    First we validate the patient and organization entries, followed by the validation of the encounter entries. 
    This method does not perform any DB modifications.
    """
    records = {name: _read_table(data_dir, name) for name in SPECS}
    parents = {
        name: {
            item["data"][ID_COLUMNS[name]]: item["data"]
            for item in records[name]
            if not item["reasons"]
        }
        for name in ("patients", "organizations")
    }
    warnings = []
    for item in records["encounters"]:
        if item["reasons"]:
            continue
        data = item["data"]
        patient = parents["patients"].get(data["patient_id"])
        if patient is None:
            item["reasons"].append("patient_reference_missing_or_rejected")
        if data["organization_id"] not in parents["organizations"]:
            item["reasons"].append("organization_reference_missing_or_rejected")
        # Dates are compared in UTC; a same-day record remains valid because the
        # source supplies no time of birth/death.
        if patient and data["start_time"].date() < patient["birth_date"]:
            item["reasons"].append("encounter_before_birth")
        if not item["reasons"] and patient["death_date"] is not None:
            if data["start_time"].date() > patient["death_date"]:
                warnings.append({
                    "table": "encounters", "source_row": item["source_row"],
                    "id": str(data["encounter_id"]), "reason": "encounter_after_death_retained",
                })

    report = {
        "status": "validated", "record_numbering": "header is record 1; first data record is 2",
        "selection": "all rows of patients.csv, organizations.csv, encounters.csv; selected columns only",
        "source_files": {}, "tables": {}, "rejected": [], "corrections": [],
        "warnings": warnings,
        "warning_counts": dict(Counter(item["reason"] for item in warnings)),
        "policy": {
            "duplicates": "identical projected rows: keep first; conflicting IDs: reject every instance",
            "missing_optional": "blank death_date, stop_time or state becomes NULL; not a correction",
            "post_death": "retain and flag; do not invent a corrected date",
        },
    }
    tables = {}
    for name, items in records.items():
        accepted = [item for item in items if not item["reasons"]]
        rejected = [item for item in items if item["reasons"]]
        tables[name] = [item["data"] for item in accepted]
        correction_counts = Counter()
        corrected_cells = 0
        for item in accepted:
            if item["corrections"]:
                correction_counts.update(event["reason"] for event in item["corrections"])
                corrected_cells += len({event["column"] for event in item["corrections"]})
                report["corrections"].append({
                    "table": name, "source_row": item["source_row"],
                    "id": str(item["data"][ID_COLUMNS[name]]), "events": item["corrections"],
                })
        for item in rejected:
            report["rejected"].append({
                "table": name, "source_row": item["source_row"],
                "id": str(item["data"].get(ID_COLUMNS[name], "unparseable")),
                "reasons": sorted(set(item["reasons"])),
            })
        report["source_files"][name + ".csv"] = sha256_file(Path(data_dir) / f"{name}.csv")
        report["tables"][name] = {
            "input_rows": len(items), "accepted_rows": len(accepted), "rejected_rows": len(rejected),
            "corrected_rows": sum(bool(item["corrections"]) for item in accepted),
            "correction_cells": corrected_cells, "correction_reasons": dict(correction_counts),
            "rejection_reasons": dict(Counter(
                reason for item in rejected for reason in set(item["reasons"])
            )),
            "expected_nulls": {
                column: sum(item["data"][column] is None for item in accepted)
                for column, _, nullable in SPECS[name].values() if nullable
            },
        }
    return tables, report
