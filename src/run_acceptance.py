"""The tables were created in a new database, and testing was done using sample data. 
  The full dataset was then loaded two times to save the test results to determine whether everything was working properly.."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import platform
from pathlib import Path

from .create_schema import create_schema, ROOT
from .db import get_engine
from .ingest_data import load
from .verify_ingestion import verify, compare_reports, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--manifest", type=Path, default=Path("data/subset_manifest.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("evidence/reproduced"))
    args = parser.parse_args()
    output = args.output_dir
    if output.exists() and any(output.iterdir()):
        parser.error("Choose an empty output directory to preserve previous evidence.")
    output.mkdir(parents=True, exist_ok=True)
    engine = get_engine()
    try:
        create_schema(engine)
        load(engine, ROOT / "tests/fixtures/valid", output / "smoke_load.json")
        smoke = verify(engine, output / "smoke_verify.json", ROOT / "tests/fixtures/valid")
        if not smoke["passed"]:
            raise RuntimeError("Small fixture check failed; full load was not attempted.")
        load(engine, args.data_dir, output / "load1.json", args.manifest)
        first = verify(engine, output / "verify1.json", args.data_dir)
        load(engine, args.data_dir, output / "load2.json", args.manifest)
        second = verify(engine, output / "verify2.json", args.data_dir)
        comparison = compare_reports(first, second)
        comparison["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(output / "rerun_comparison.json", comparison)
        write_json(output / "environment.json", {
            "python": platform.python_version(), "platform": platform.system(),
            "postgresql": second["postgresql_version"],
            "packages": {name: importlib.metadata.version(name) for name in ("pandas", "SQLAlchemy", "psycopg", "psycopg-binary")},
            "source_scope": "All rows of patients.csv, organizations.csv, encounters.csv; projected fields only.",
        })
        if not comparison["passed"]:
            raise RuntimeError("Acceptance failed. Inspect the retained verification reports.")
        print("PASS: small fixture, full source load, source-to-database reconciliation, and unchanged rerun.")
        print(f"Evidence: {output}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
