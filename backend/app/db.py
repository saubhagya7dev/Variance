from pathlib import Path

from sqlalchemy import Engine, event
from sqlmodel import create_engine


def make_engine(url: str) -> Engine:
    if not url.startswith("sqlite:///"):
        raise ValueError("This local release supports SQLite only.")
    filename = url.removeprefix("sqlite:///")
    if filename != ":memory:":
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})

    @event.listens_for(engine, "connect")
    def configure(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
        dbapi_connection.execute("PRAGMA busy_timeout=15000")

    return engine


def migrate(engine: Engine) -> None:
    with engine.connect() as db:
        db.exec_driver_sql("PRAGMA journal_mode=WAL")
        db.commit()
        db.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            db.exec_driver_sql(
                "CREATE TABLE IF NOT EXISTS schema_versions(version INTEGER PRIMARY KEY)"
            )
            versions = {r[0] for r in db.exec_driver_sql("SELECT version FROM schema_versions")}
            for path in sorted((Path(__file__).parent / "migrations").glob("*.sql")):
                version = int(path.stem.split("_")[0])
                if version in versions:
                    continue
                # These versioned DDL files contain simple statements, no triggers or SQL literals with semicolons.
                for statement in path.read_text(encoding="utf-8").split(";"):
                    if statement.strip():
                        db.exec_driver_sql(statement)
                db.exec_driver_sql("INSERT INTO schema_versions VALUES (?)", (version,))
            db.commit()
        except Exception:
            db.rollback()
            raise
