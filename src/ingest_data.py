"""We inspect the source data and import all three tables of Phase 1 in one transaction."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from sqlalchemy import MetaData, text
from sqlalchemy.exc import SQLAlchemyError

from .db import get_engine
from .validation import SPECS, validate_directory, verify_manifest


def write_report(path, report):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def load(engine, data_dir, report_path, manifest_path=None):
    """Verify the input data and then proceed with overwriting the rows in source tables.

       We don’t change the existing tables, constraints, and indexes. 
       All the deletes and inserts will be committed as a single transaction or rolled back as a single transaction. 
       We use an advisory lock to ensure that there is just one loader process at a time. 
       Other processes are supposed not to update the source schema during this period.
    """
    report = {"status": "failed_validation"}
    try:
        if manifest_path is not None:
            verify_manifest(data_dir, manifest_path)
        tables, report = validate_directory(data_dir)
        report["started_at_utc"] = datetime.now(timezone.utc).isoformat()
        report["load_strategy"] = "transactional_full_reload"
        report["manifest_checked"] = manifest_path is not None
        empty = [name for name, rows in tables.items() if not rows]
        if empty:
            raise ValueError("Refusing reload with empty accepted tables: " + ", ".join(empty))
    except Exception as exc:
        report["status"] = "failed_validation"
        report["failure_type"] = type(exc).__name__
        report["failure_message"] = str(exc)
        write_report(report_path, report)
        raise

    try:
        with engine.begin() as connection:
            connection.execute(text("SELECT pg_advisory_xact_lock(550, 1)"))
            metadata = MetaData(schema="source")
            metadata.reflect(bind=connection, only=list(SPECS))
            db_tables = {name: metadata.tables[f"source.{name}"] for name in SPECS}
            for name in ("encounters", "patients", "organizations"):
                connection.execute(db_tables[name].delete())
            for name in ("patients", "organizations", "encounters"):
                for offset in range(0, len(tables[name]), 1000):
                    connection.execute(db_tables[name].insert(), tables[name][offset:offset + 1000])
    except Exception as exc:
        report["status"] = "database_transaction_failed"
        report["failure_type"] = type(exc).__name__
        report["failure_message"] = "Transaction failed; prior source rows were preserved by rollback."
        write_report(report_path, report)
        raise
    report["status"] = "committed"
    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_report(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--manifest", type=Path,
                        help="Validate the selected CSV hashes against this manifest; omit only for fixtures")
    args = parser.parse_args()
    engine = None
    try:
        engine = get_engine()
        report = load(engine, args.data_dir, args.report, args.manifest)
        counts = {name: stats["accepted_rows"] for name, stats in report["tables"].items()}
        print(json.dumps({"status": report["status"], "rows": counts, "report": str(args.report)}))
        return 0
    except (ValueError, OSError, SQLAlchemyError) as exc:
        print(f"Ingestion failed ({type(exc).__name__}); check settings and the validation report.", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
