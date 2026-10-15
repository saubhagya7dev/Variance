"""Workspace-scoped domain operations. No external side effects or paid APIs."""
import base64
import binascii
import hashlib
import io
import json
import re
import time
import zipfile
from datetime import date
from urllib.parse import urlsplit

from .store import Store, encode, event, now, uid


class Invalid(ValueError):
    pass


def field(data: dict, key: str, maximum: int = 2000, optional: bool = False) -> str:
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > maximum or (not optional and not value.strip()):
        raise Invalid(f'{key}: enter text between 1 and {maximum} characters.')
    return value.strip()


def public_url(value: str) -> str:
    try:
        p = urlsplit(value)
        if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password or any(c.isspace() for c in value):
            raise ValueError()
    except ValueError:
        raise Invalid('Enter a complete http or https source URL.') from None
    return value


def integer(data: dict, key: str, low: int = 0, high: int = 1_000_000_000) -> int:
    value = data.get(key)
    if type(value) is not int or not low <= value <= high:
        raise Invalid(f'{key} must be an integer between {low} and {high}.')
    return value


def iso_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise Invalid('Use a valid YYYY-MM-DD date.') from None


def campaign(db, workspace: str, cid: str):
    row = db.execute('SELECT * FROM campaigns WHERE id=? AND workspace_id=?', (cid, workspace)).fetchone()
    if not row:
        raise Invalid('Campaign not found in this workspace.')
    return row, json.loads(row['document'])


def save(db, row, doc: dict, state: str | None = None):
    db.execute('UPDATE campaigns SET document=?,state=?,updated=? WHERE id=? AND workspace_id=?',
               (encode(doc), state or row['state'], now(), row['id'], row['workspace_id']))


def approved(db, workspace: str, cid: str):
    row = db.execute('''SELECT a.* FROM assets a JOIN approvals p ON p.asset_id=a.id AND p.digest=a.digest
        WHERE a.workspace_id=? AND a.campaign_id=? AND p.workspace_id=? AND p.revoked=0 AND a.status='approved'
        ORDER BY p.rowid DESC LIMIT 1''', (workspace, cid, workspace)).fetchone()
    if not row:
        raise Invalid('An explicit human image approval is required.')
    return row


def enqueue(db, workspace: str, cid: str, kind: str, key: str, priority: int = 50) -> str:
    if kind not in ('research', 'creative', 'package', 'analyze'):
        raise Invalid('Unknown specialist task.')
    row, doc = campaign(db, workspace, cid)
    previous = db.execute('SELECT * FROM jobs WHERE workspace_id=? AND idem=?', (workspace, key)).fetchone()
    if previous:
        if previous['campaign_id'] != cid or previous['kind'] != kind:
            raise Invalid('Idempotency key already belongs to another task.')
        return previous['id']
    if kind == 'creative' and not doc.get('research'):
        raise Invalid('Research must complete before creative direction.')
    if kind == 'creative' and doc.get('brief'):
        raise Invalid('A brief already exists; edit the master prompt instead.')
    if kind == 'research' and doc.get('research'):
        raise Invalid('Research has already completed for this evidence record.')
    if kind == 'package':
        if not doc.get('brief'):
            raise Invalid('Create a brief first.')
        approved(db, workspace, cid)
    if kind == 'analyze' and not doc.get('metrics'):
        raise Invalid('Record real performance metrics before analysis.')
    if db.execute("SELECT 1 FROM jobs WHERE workspace_id=? AND campaign_id=? AND kind=? AND status IN ('queued','running')", (workspace, cid, kind)).fetchone():
        raise Invalid('This task is already queued or running.')
    jid = uid()
    db.execute('INSERT INTO jobs(id,workspace_id,campaign_id,kind,status,priority,available,idem,created) VALUES(?,?,?,?,?,?,?,?,?)',
               (jid, workspace, cid, kind, 'queued', priority, time.time(), key, now()))
    event(db, workspace, cid, 'orchestrator', 'job.queued', {'job': jid, 'kind': kind, 'contract': 1})
    return jid


class Service:
    def __init__(self, store: Store):
        self.store = store

    def snapshot(self, workspace: str) -> dict:
        with self.store.connect() as db:
            ws = dict(db.execute('SELECT * FROM workspaces WHERE id=?', (workspace,)).fetchone())
            ws['profile'] = json.loads(ws['profile'])
            campaigns = []
            for r in db.execute('SELECT * FROM campaigns WHERE workspace_id=? ORDER BY created DESC,rowid DESC', (workspace,)):
                item = dict(r)
                item['document'] = json.loads(item['document'])
                item['assets'] = [dict(a) for a in db.execute('SELECT id,name,mime,digest,status,created FROM assets WHERE workspace_id=? AND campaign_id=? ORDER BY rowid DESC', (workspace, r['id']))]
                campaigns.append(item)
            jobs = [dict(r) for r in db.execute('SELECT * FROM jobs WHERE workspace_id=? ORDER BY rowid DESC LIMIT 100', (workspace,))]
            events = [dict(r) for r in db.execute('SELECT * FROM events WHERE workspace_id=? ORDER BY id DESC LIMIT 150', (workspace,))]
            return {'workspace': ws, 'campaigns': campaigns, 'jobs': jobs, 'events': events}

    def profile(self, workspace: str, actor: str, data: dict):
        profile = {k: field(data, k, 1500) for k in ('niche', 'audience', 'style', 'constraints')}
        with self.store.transaction() as db:
            db.execute('UPDATE workspaces SET profile=? WHERE id=?', (encode(profile), workspace))
            event(db, workspace, None, actor, 'profile.updated', profile)

    def create(self, workspace: str, actor: str, data: dict) -> str:
        title = field(data, 'title', 160)
        doc = {'source': public_url(field(data, 'source', 2000)), 'evidence': field(data, 'evidence', 6000),
               'source_date': iso_date(field(data, 'source_date', 10)), 'priority': integer(data, 'priority', 1, 100),
               'provenance': 'User-supplied evidence; not independently verified', 'captured_at': now()}
        cid = uid()
        with self.store.transaction() as db:
            db.execute('INSERT INTO campaigns VALUES(?,?,?,?,?,?,?)', (cid, workspace, title, 'research_queued', encode(doc), now(), now()))
            event(db, workspace, cid, actor, 'evidence.captured', doc)
            enqueue(db, workspace, cid, 'research', 'initial-' + cid, doc['priority'])
        return cid

    def task(self, workspace: str, cid: str, data: dict) -> str:
        with self.store.transaction() as db:
            return enqueue(db, workspace, cid, field(data, 'kind', 30), field(data, 'key', 120))

    def prompt(self, workspace: str, cid: str, actor: str, data: dict):
        prompt = field(data, 'prompt', 16000)
        with self.store.transaction() as db:
            row, doc = campaign(db, workspace, cid)
            if not doc.get('brief'):
                raise Invalid('Create a creative brief first.')
            doc.setdefault('prompt_history', []).append({'prompt': doc['brief']['prompt'], 'version': doc['brief']['version'], 'saved': now()})
            doc['brief']['prompt'] = prompt
            doc['brief']['version'] += 1
            doc.pop('packages', None)
            save(db, row, doc, 'approved' if self._has_approval(db, workspace, cid) else 'awaiting_image')
            event(db, workspace, cid, actor, 'prompt.edited', {'version': doc['brief']['version'], 'prompt': prompt})

    @staticmethod
    def _has_approval(db, workspace, cid):
        try:
            return bool(approved(db, workspace, cid))
        except Invalid:
            return False

    def upload(self, workspace: str, cid: str, actor: str, data: dict) -> str:
        name = field(data, 'name', 160)
        try:
            raw = base64.b64decode(field(data, 'body', 7_000_000), validate=True)
        except (ValueError, binascii.Error):
            raise Invalid('Invalid image encoding.') from None
        if not 16 <= len(raw) <= 5 * 1024 * 1024:
            raise Invalid('Images must be between 16 bytes and 5 MB.')
        # Strict format signatures; never accept SVG, HTML or client-supplied MIME.
        if raw.startswith(b'\x89PNG\r\n\x1a\n') and len(raw) >= 33 and raw[12:16] == b'IHDR' and b'IEND' in raw[-12:]:
            mime = 'image/png'
            width, height = int.from_bytes(raw[16:20], 'big'), int.from_bytes(raw[20:24], 'big')
            if not 0 < width <= 16000 or not 0 < height <= 16000 or width * height > 64_000_000:
                raise Invalid('Image dimensions exceed the 64 megapixel limit.')
        elif raw[:3] == b'\xff\xd8\xff' and raw[-2:] == b'\xff\xd9':
            mime = 'image/jpeg'
        elif raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' and int.from_bytes(raw[4:8], 'little') == len(raw) - 8:
            mime = 'image/webp'
        else:
            raise Invalid('Upload a complete PNG, JPEG, or WebP image. SVG is not supported.')
        aid, digest = uid(), hashlib.sha256(raw).hexdigest()
        with self.store.transaction() as db:
            row, doc = campaign(db, workspace, cid)
            if not doc.get('brief'):
                raise Invalid('Create a brief before importing images.')
            if db.execute('SELECT 1 FROM assets WHERE workspace_id=? AND campaign_id=? AND digest=?', (workspace, cid, digest)).fetchone():
                raise Invalid('This image is already imported.')
            db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?)', (aid, workspace, cid, name, mime, digest, raw, 'pending', now()))
            if not self._has_approval(db, workspace, cid):
                save(db, row, doc, 'awaiting_approval')
            event(db, workspace, cid, actor, 'image.imported', {'asset': aid, 'digest': digest, 'name': name})
        return aid

    def decide(self, workspace: str, cid: str, aid: str, actor: str, data: dict):
        decision = field(data, 'decision', 20)
        if decision not in ('approved', 'rejected'):
            raise Invalid('Choose approved or rejected.')
        if data.get('confirmed') is not True:
            raise Invalid('Explicit human confirmation is required.')
        with self.store.transaction() as db:
            row, doc = campaign(db, workspace, cid)
            asset = db.execute('SELECT * FROM assets WHERE id=? AND workspace_id=? AND campaign_id=?', (aid, workspace, cid)).fetchone()
            if not asset:
                raise Invalid('Image not found.')
            if decision == 'approved':
                db.execute("UPDATE assets SET status='pending' WHERE workspace_id=? AND campaign_id=? AND status='approved'", (workspace, cid))
                db.execute('UPDATE approvals SET revoked=1 WHERE workspace_id=? AND campaign_id=?', (workspace, cid))
                db.execute('INSERT INTO approvals VALUES(?,?,?,?,?,?,?,0)', (uid(), workspace, cid, aid, asset['digest'], actor, now()))
            else:
                db.execute('UPDATE approvals SET revoked=1 WHERE workspace_id=? AND asset_id=?', (workspace, aid))
            db.execute('UPDATE assets SET status=? WHERE id=? AND workspace_id=?', (decision, aid, workspace))
            doc.pop('packages', None)
            save(db, row, doc, 'approved' if self._has_approval(db, workspace, cid) else 'awaiting_approval')
            event(db, workspace, cid, actor, 'image.' + decision, {'asset': aid, 'digest': asset['digest']})

    def packages(self, workspace: str, cid: str, actor: str, data: dict):
        platform = field(data, 'platform', 20)
        limits = {'instagram': 2200, 'facebook': 5000, 'x': 280}
        if platform not in limits:
            raise Invalid('Unsupported platform.')
        caption = field(data, 'caption', limits[platform])
        alt = field(data, 'alt', 1000)
        with self.store.transaction() as db:
            row, doc = campaign(db, workspace, cid)
            approved(db, workspace, cid)
            if platform not in doc.get('packages', {}):
                raise Invalid('Prepare packages first.')
            doc['packages'][platform].update(caption=caption, alt=alt)
            save(db, row, doc)
            event(db, workspace, cid, actor, 'package.edited', {'platform': platform, 'caption': caption, 'alt': alt})

    def export(self, workspace: str, cid: str, actor: str) -> bytes:
        with self.store.transaction() as db:
            row, doc = campaign(db, workspace, cid)
            asset = approved(db, workspace, cid)
            if not doc.get('packages') or doc.get('package_asset') != asset['id']:
                raise Invalid('Prepare packages for the current approved image first.')
            result = io.BytesIO()
            ext = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp'}[asset['mime']]
            with zipfile.ZipFile(result, 'w', zipfile.ZIP_DEFLATED) as z:
                z.writestr('approved-image.' + ext, asset['body'])
                z.writestr('packages.json', encode(doc['packages']))
                z.writestr('provenance.json', encode({'source': doc['source'], 'evidence': doc['evidence'], 'asset_sha256': asset['digest'], 'prompt': doc['brief'], 'exported_at': now()}))
                for platform, package in doc['packages'].items():
                    z.writestr(platform + '.txt', package['caption'] + '\n\nAlt text: ' + package['alt'])
                z.writestr('README.txt', 'Manual export only. No post has been published. Review platform rules, rights, image dimensions and final text before posting. Record publication and measured metrics in Variance afterward.')
            event(db, workspace, cid, actor, 'package.exported', {'asset': asset['id'], 'digest': asset['digest']})
            save(db, row, doc, 'exported')
            return result.getvalue()

    def publication(self, workspace: str, cid: str, actor: str, data: dict):
        platform = field(data, 'platform', 20)
        if platform not in ('instagram', 'facebook', 'x') or data.get('confirmed') is not True:
            raise Invalid('Choose a platform and explicitly confirm manual publication.')
        url = public_url(field(data, 'url', 2000))
        with self.store.transaction() as db:
            row, doc = campaign(db, workspace, cid)
            asset = approved(db, workspace, cid)
            if not doc.get('packages'):
                raise Invalid('Prepare the approved publication package first.')
            publication = {'id': uid(), 'platform': platform, 'url': url, 'asset': asset['id'], 'digest': asset['digest'], 'recorded_at': now(), 'provenance': 'Creator-confirmed manual publication; not API verified'}
            doc.setdefault('publications', []).append(publication)
            save(db, row, doc, 'published')
            event(db, workspace, cid, actor, 'publication.recorded', publication)

    def metrics(self, workspace: str, cid: str, actor: str, data: dict):
        metric = {k: integer(data, k) for k in ('impressions', 'likes', 'comments', 'shares', 'saves')}
        metric.update(platform=field(data, 'platform', 20), period=field(data, 'period', 120), provenance=field(data, 'provenance', 1000), recorded_at=now())
        metric['comment_notes'] = field(data, 'comment_notes', 4000, optional=True)
        with self.store.transaction() as db:
            row, doc = campaign(db, workspace, cid)
            if not any(p['platform'] == metric['platform'] for p in doc.get('publications', [])):
                raise Invalid('Record publication on this platform before adding metrics.')
            # One latest snapshot per platform prevents summing overlapping periods.
            doc.setdefault('metrics', {})[metric['platform']] = metric
            doc.pop('analysis', None)
            save(db, row, doc)
            event(db, workspace, cid, actor, 'metrics.recorded', metric)
            enqueue(db, workspace, cid, 'analyze', uid())

    def job_action(self, workspace: str, jid: str, action: str):
        with self.store.transaction() as db:
            job = db.execute('SELECT * FROM jobs WHERE id=? AND workspace_id=?', (jid, workspace)).fetchone()
            if not job:
                raise Invalid('Job not found.')
            if action == 'cancel' and job['status'] in ('queued', 'running'):
                db.execute("UPDATE jobs SET status='cancelled',lease=NULL WHERE id=?", (jid,))
                event(db, workspace, job['campaign_id'], 'orchestrator', 'job.cancelled', {'job': jid})
            elif action == 'retry' and job['status'] in ('failed', 'cancelled'):
                enqueue(db, workspace, job['campaign_id'], job['kind'], uid(), job['priority'])
            else:
                raise Invalid('This job cannot be ' + action + 'ed.')
