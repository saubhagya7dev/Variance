"""SQLite persistence, migrations, and explicit transaction boundaries."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def uid() -> str:
    return uuid4().hex


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY)')
            versions = {r[0] for r in db.execute('SELECT version FROM schema_migrations')}
            for migration in sorted((Path(__file__).parent / 'migrations').glob('*.sql')):
                if int(migration.stem.split('_')[0]) not in versions:
                    db.executescript('BEGIN IMMEDIATE;\n' + migration.read_text() + '\nCOMMIT;')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise


def event(db, workspace: str, campaign: str | None, actor: str, kind: str, detail: object):
    db.execute('INSERT INTO events(workspace_id,campaign_id,actor,kind,detail,created) VALUES(?,?,?,?,?,?)',
               (workspace, campaign, actor, kind, encode(detail), now()))
