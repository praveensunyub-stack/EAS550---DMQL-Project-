from pathlib import Path
from sqlalchemy import text
from .db import get_engine

ROOT = Path(__file__).resolve().parents[1]


def create_schema(engine):
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        exists = connection.execute(text("SELECT to_regnamespace('source') IS NOT NULL")).scalar_one()
        if exists:
            raise ValueError("The source schema already exists. Use ingestion to reload, or choose a fresh database.")
        connection.exec_driver_sql((ROOT / "schema.sql").read_text(encoding="utf-8"))


def main():
    engine = get_engine()
    try:
        create_schema(engine)
        print("Created the three Phase 1 source tables.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
