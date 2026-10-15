"""Password hashing and revocable server-side sessions."""
import hashlib
import hmac
import re
import secrets
import sqlite3
import time

from .domain import Invalid, field
from .store import encode, now, uid

DEFAULT_PROFILE = {'niche': 'Entertainment and original digital art', 'audience': 'Curious fans and visual culture enthusiasts',
                   'style': 'Cinematic editorial illustration, considered typography, rich color and expressive lighting',
                   'constraints': 'Original artwork. Verify references, rights, likeness and platform policies. No misleading official affiliation.'}


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 600_000).hex()
    return salt + ':' + value


def authenticate(store, data: dict, register: bool = False):
    email = field(data, 'email', 254).lower()
    password = field(data, 'password', 256)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(password) < 12:
        raise Invalid('Enter a valid email and a password of at least 12 characters.')
    # Hash outside the database lock; use a dummy salt to avoid a cheap unknown-user path.
    with store.connect() as db:
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    hashed = password_hash(password, user['password'].split(':')[0] if user and not register else None)
    if not register and (not user or not hmac.compare_digest(hashed, user['password'])):
        raise Invalid('Email or password is incorrect.')
    with store.transaction() as db:
        if register:
            user_id, workspace = uid(), uid()
            try:
                db.execute('INSERT INTO users VALUES(?,?,?,?)', (user_id, email, hashed, now()))
            except sqlite3.IntegrityError:
                raise Invalid('Unable to create this account. Try signing in.') from None
            db.execute('INSERT INTO workspaces VALUES(?,?,?)', (workspace, field(data, 'name', 80), encode(DEFAULT_PROFILE)))
            db.execute('INSERT INTO memberships VALUES(?,?)', (user_id, workspace))
        else:
            user_id = user['id']
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        db.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        db.execute('INSERT INTO sessions VALUES(?,?,?,?)', (digest(token), user_id, csrf, time.time() + 86400))
    return token, csrf


def session(store, token: str):
    with store.connect() as db:
        row = db.execute('SELECT s.*,u.email FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?', (digest(token), time.time())).fetchone()
        if not row:
            return None
        result = dict(row)
        result['workspaces'] = [dict(w) for w in db.execute('SELECT w.id,w.name FROM workspaces w JOIN memberships m ON m.workspace_id=w.id WHERE m.user_id=?', (row['user_id'],))]
        return result
