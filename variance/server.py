"""Local HTTP transport. All state-changing API calls require a same-origin session."""
import argparse
import json
import logging
import os
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .auth import authenticate, digest, session
from .domain import Invalid, Service
from .store import Store
from .worker import Worker

STATIC = Path(__file__).parent / 'static'
log = logging.getLogger('variance.http')


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store, registration=True, secure_cookie=False):
        super().__init__(address, Handler)
        self.store, self.service = store, Service(store)
        self.registration, self.secure_cookie = registration, secure_cookie
        self.attempts = {}
        self.rate_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = 'Variance'

    def log_message(self, format, *args):
        log.info('request method=%s path=%s status=%s', self.command, urlsplit(self.path).path, args[1] if len(args) > 1 else '-')

    def reply(self, status, value, mime='application/json', extra=None):
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False).encode() if mime == 'application/json' else value
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'")
        for key, val in (extra or {}).items():
            self.send_header(key, val)
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def dispatch(self):
        try:
            self.route()
        except Invalid as exc:
            self.reply(400, {'error': str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            log.exception('request_failed method=%s', self.command)
            self.reply(500, {'error': 'Unexpected server error. Check server logs.'})

    def body(self):
        if self.headers.get('Transfer-Encoding'):
            raise Invalid('Chunked requests are not supported.')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise Invalid('Invalid request size.') from None
        if not 0 < length <= 7_100_000:
            raise Invalid('Request is empty or exceeds the 7 MB limit.')
        if self.headers.get_content_type() != 'application/json':
            raise Invalid('Use application/json.')
        try:
            value = json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        except (ValueError, UnicodeError):
            raise Invalid('Invalid JSON request.') from None
        if not isinstance(value, dict):
            raise Invalid('A JSON object is required.')
        return value

    def route(self):
        parsed = urlsplit(self.path)
        path = parsed.path
        if self.command == 'GET' and path in ('/', '/app.js', '/style.css'):
            file = STATIC / ('index.html' if path == '/' else path[1:])
            mime = {'.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8'}[file.suffix]
            return self.reply(200, file.read_bytes(), mime)
        if path == '/api/health' and self.command == 'GET':
            with self.server.store.connect() as db:
                db.execute('SELECT 1').fetchone()
            return self.reply(200, {'status': 'ok', 'mode': 'local', 'external_publishing': False})
        if not path.startswith('/api/'):
            return self.reply(404, {'error': 'Not found.'})
        if self.command == 'POST':
            # Reject cross-origin and cross-site writes including login/registration.
            origin = self.headers.get('Origin')
            if (origin and origin not in ('http://' + self.headers.get('Host', ''), 'https://' + self.headers.get('Host', ''))) or self.headers.get('Sec-Fetch-Site') == 'cross-site':
                return self.reply(403, {'error': 'Cross-origin requests are forbidden.'})
        if path in ('/api/login', '/api/register') and self.command == 'POST':
            with self.server.rate_lock:
                current = time.time()
                # Bound memory and use a fixed ten-attempt / minute local auth budget.
                self.server.attempts = {k: v for k, v in self.server.attempts.items() if current - v[0] < 60}
                start, count = self.server.attempts.get(self.client_address[0], (current, 0))
                if count >= 10:
                    return self.reply(429, {'error': 'Too many sign-in attempts. Try again in one minute.'})
                self.server.attempts[self.client_address[0]] = (start, count + 1)
            if path == '/api/register' and not self.server.registration:
                return self.reply(403, {'error': 'New account registration is disabled.'})
            token, csrf = authenticate(self.server.store, self.body(), path == '/api/register')
            cookie = 'variance_session=' + token + '; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'
            if self.server.secure_cookie:
                cookie += '; Secure'
            return self.reply(200, {'csrf': csrf}, extra={'Set-Cookie': cookie})
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
        except Exception:
            return self.reply(401, {'error': 'Please sign in.'})
        token = cookie['variance_session'].value if 'variance_session' in cookie else ''
        user = session(self.server.store, token)
        if not user:
            return self.reply(401, {'error': 'Please sign in.'})
        if self.command == 'GET' and path == '/api/me':
            return self.reply(200, {k: user[k] for k in ('email', 'csrf', 'workspaces')})
        if self.command == 'POST' and self.headers.get('X-CSRF-Token') != user['csrf']:
            return self.reply(403, {'error': 'Invalid session token. Refresh and try again.'})
        if path == '/api/logout' and self.command == 'POST':
            with self.server.store.transaction() as db:
                db.execute('DELETE FROM sessions WHERE token=?', (digest(token),))
            return self.reply(200, {'ok': True}, extra={'Set-Cookie': 'variance_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'})
        query = parse_qs(parsed.query)
        workspace = self.headers.get('X-Workspace') or query.get('workspace', [''])[0]
        if workspace not in {w['id'] for w in user['workspaces']}:
            return self.reply(403, {'error': 'Workspace access denied.'})
        service, actor = self.server.service, user['user_id']
        if path == '/api/snapshot' and self.command == 'GET':
            return self.reply(200, service.snapshot(workspace))
        parts = path.strip('/').split('/')
        if len(parts) == 3 and parts[1] == 'assets' and self.command == 'GET':
            with self.server.store.connect() as db:
                asset = db.execute('SELECT mime,body FROM assets WHERE id=? AND workspace_id=?', (parts[2], workspace)).fetchone()
            if not asset:
                return self.reply(404, {'error': 'Image not found.'})
            return self.reply(200, asset['body'], asset['mime'])
        if len(parts) == 4 and parts[1] == 'campaigns' and parts[3] == 'export' and self.command == 'GET':
            # Download creates an audit event; does not publish externally or mutate approval.
            return self.reply(200, service.export(workspace, parts[2], actor), 'application/zip', {'Content-Disposition': 'attachment; filename="variance-publication.zip"'})
        if self.command != 'POST':
            return self.reply(404, {'error': 'Unknown endpoint.'})
        data = self.body()
        if path == '/api/profile':
            service.profile(workspace, actor, data)
        elif path == '/api/campaigns':
            return self.reply(201, {'id': service.create(workspace, actor, data)})
        elif len(parts) == 4 and parts[1] == 'campaigns':
            cid, action = parts[2:]
            if action == 'tasks':
                return self.reply(202, {'id': service.task(workspace, cid, data)})
            if action == 'prompt':
                service.prompt(workspace, cid, actor, data)
            elif action == 'assets':
                return self.reply(201, {'id': service.upload(workspace, cid, actor, data)})
            elif action == 'decision':
                service.decide(workspace, cid, str(data.get('asset', '')), actor, data)
            elif action == 'packages':
                service.packages(workspace, cid, actor, data)
            elif action == 'publication':
                service.publication(workspace, cid, actor, data)
            elif action == 'metrics':
                service.metrics(workspace, cid, actor, data)
            else:
                return self.reply(404, {'error': 'Unknown campaign action.'})
        elif len(parts) == 4 and parts[1] == 'jobs':
            service.job_action(workspace, parts[2], parts[3])
        else:
            return self.reply(404, {'error': 'Unknown endpoint.'})
        return self.reply(200, {'ok': True})


def main():
    parser = argparse.ArgumentParser(description='Variance local creative workspace')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-worker', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    store = Store(os.environ.get('VARIANCE_DB', 'data/variance.sqlite3'))
    server = Server((args.host, args.port), store, os.environ.get('VARIANCE_REGISTRATION', '1') == '1', os.environ.get('VARIANCE_SECURE_COOKIE', '0') == '1')
    worker = Worker(store)
    if not args.no_worker:
        threading.Thread(target=worker.run, name='variance-worker', daemon=True).start()
    print(f'Variance Local: http://{args.host}:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        worker.stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
