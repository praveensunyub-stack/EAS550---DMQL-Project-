import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL


def get_engine():
    required = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "PGSSLMODE")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise ValueError("Set these environment variables: " + ", ".join(missing))
    try:
        port = int(os.environ["PGPORT"])
    except ValueError as exc:
        raise ValueError("PGPORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("PGPORT must be between 1 and 65535")
    sslmode = os.environ["PGSSLMODE"]
    if sslmode not in {"disable", "allow", "prefer", "require", "verify-ca", "verify-full"}:
        raise ValueError("PGSSLMODE is not a supported libpq SSL mode")
    url = URL.create(
        "postgresql+psycopg",
        username=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.environ["PGHOST"],
        port=port,
        database=os.environ["PGDATABASE"],
        query={"sslmode": sslmode, "connect_timeout": "10"},
    )
    return create_engine(url, pool_pre_ping=True, hide_parameters=True)
