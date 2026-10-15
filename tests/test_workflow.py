"""Meaningful end-to-end service and transport tests; no network providers required."""
import base64
import io
import json
import logging
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from unittest.mock import patch

from variance.auth import authenticate, session
from variance.domain import Invalid, Service
from variance.server import Server
from variance.store import Store
from variance.worker import Worker

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aQ1cAAAAASUVORK5CYII=')


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(str(Path(self.tmp.name) / 'test.sqlite3'))
        self.service, self.worker = Service(self.store), Worker(self.store)
        token, self.csrf = authenticate(self.store, {'email': 'creator@example.test', 'password': 'test-password-123', 'name': 'Test studio'}, True)
        self.user = session(self.store, token)
        self.actor, self.ws = self.user['user_id'], self.user['workspaces'][0]['id']
        self.cid = self.service.create(self.ws, self.actor, {'title':'Original editorial study','source':'https://example.org/source','source_date':'2026-10-01','evidence':'An excerpt supplied by the creator, not verified by the application.','priority':80})

    def tearDown(self):
        self.tmp.cleanup()

    def doc(self):
        return next(c for c in self.service.snapshot(self.ws)['campaigns'] if c['id'] == self.cid)['document']

    def creative(self):
        self.assertTrue(self.worker.tick())
        self.service.task(self.ws, self.cid, {'kind':'creative','key':'creative'})
        self.worker.tick()

    def approve(self):
        self.creative()
        aid = self.service.upload(self.ws,self.cid,self.actor,{'name':'candidate.png','body':base64.b64encode(PNG).decode()})
        self.service.decide(self.ws,self.cid,aid,self.actor,{'decision':'approved','confirmed':True})
        return aid

    def package(self):
        aid = self.approve()
        self.service.task(self.ws,self.cid,{'kind':'package','key':'package'})
        self.worker.tick()
        return aid

    def test_complete_lifecycle(self):
        aid = self.package()
        archive = self.service.export(self.ws,self.cid,self.actor)
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            self.assertEqual(z.read('approved-image.png'), PNG)
            self.assertEqual(set(json.loads(z.read('packages.json'))), {'instagram','facebook','x'})
            self.assertIn('No post has been published', z.read('README.txt').decode())
        self.assertNotIn('publications', self.doc())
        self.service.publication(self.ws,self.cid,self.actor,{'platform':'instagram','url':'https://www.instagram.com/p/test/','confirmed':True})
        self.service.metrics(self.ws,self.cid,self.actor,{'platform':'instagram','period':'First 7 days','provenance':'Manually transcribed Insights','impressions':1000,'likes':40,'comments':5,'shares':3,'saves':12})
        self.worker.tick()
        self.assertEqual(self.doc()['analysis']['rows'][0]['engagement_rate'],6)
        events = {e['kind'] for e in self.service.snapshot(self.ws)['events']}
        self.assertTrue({'evidence.captured','image.approved','package.exported','publication.recorded','metrics.recorded'}.issubset(events))

    def test_human_approval_required_and_revocation_invalidates(self):
        with self.assertRaises(Invalid):
            self.service.task(self.ws,self.cid,{'kind':'package','key':'unapproved'})
        aid = self.package()
        with self.assertRaises(Invalid):
            self.service.decide(self.ws,self.cid,aid,self.actor,{'decision':'approved','confirmed':False})
        self.service.decide(self.ws,self.cid,aid,self.actor,{'decision':'rejected','confirmed':True})
        self.assertNotIn('packages', self.doc())
        with self.assertRaises(Invalid):
            self.service.export(self.ws,self.cid,self.actor)

    def test_worker_rechecks_approval_when_package_queued(self):
        aid = self.approve()
        jid = self.service.task(self.ws,self.cid,{'kind':'package','key':'later'})
        self.service.decide(self.ws,self.cid,aid,self.actor,{'decision':'rejected','confirmed':True})
        with self.assertLogs('variance.worker', level='ERROR'):
            self.worker.tick()
        job = next(j for j in self.service.snapshot(self.ws)['jobs'] if j['id']==jid)
        self.assertEqual(job['status'],'failed')
        self.assertNotIn('packages', self.doc())

    def test_prompt_versions_and_package_invalidation(self):
        self.package()
        self.service.prompt(self.ws,self.cid,self.actor,{'prompt':'A revised original artwork concept.'})
        d = self.doc()
        self.assertEqual(d['brief']['version'],2)
        self.assertEqual(len(d['prompt_history']),1)
        self.assertNotIn('packages', d)

    def test_workspace_isolation(self):
        token,_ = authenticate(self.store,{'email':'second@example.test','password':'another-password-123','name':'Other studio'},True)
        other = session(self.store,token)['workspaces'][0]['id']
        self.assertEqual(self.service.snapshot(other)['campaigns'],[])
        with self.assertRaises(Invalid):
            self.service.task(other,self.cid,{'kind':'research','key':'stolen'})

    def test_idempotency_cancellation_retry_and_crash_recovery(self):
        self.worker.tick()
        first = self.service.task(self.ws,self.cid,{'kind':'creative','key':'same'})
        second = self.service.task(self.ws,self.cid,{'kind':'creative','key':'same'})
        self.assertEqual(first,second)
        self.service.job_action(self.ws,first,'cancel')
        self.assertFalse(self.worker.tick())
        self.service.job_action(self.ws,first,'retry')
        with self.store.transaction() as db:
            db.execute("UPDATE jobs SET status='running',lease=?,attempts=1 WHERE status='queued'", (time.time()-10,))
        self.assertTrue(self.worker.tick())
        self.assertIn('brief',self.doc())
        self.assertFalse(self.worker.tick())

    def test_transient_failure_retries_without_partial_output(self):
        with patch('variance.worker.run_specialist', side_effect=RuntimeError('injected')):
            with self.assertLogs('variance.worker',level='ERROR'):
                self.worker.tick()
        job=self.service.snapshot(self.ws)['jobs'][0]
        self.assertEqual(job['status'],'queued')
        self.assertEqual(job['attempts'],1)
        self.assertNotIn('research',self.doc())
        with self.store.transaction() as db:
            db.execute('UPDATE jobs SET available=0')
        self.worker.tick()
        self.assertIn('research',self.doc())

    def test_concurrent_workers_complete_once(self):
        workers=[threading.Thread(target=Worker(self.store).tick) for _ in range(4)]
        for w in workers:w.start()
        for w in workers:w.join()
        events=[e for e in self.service.snapshot(self.ws)['events'] if e['kind']=='specialist.completed']
        self.assertEqual(len(events),1)

    def test_upload_validation_and_duplicate_detection(self):
        self.creative()
        for content in (b'<svg onload="alert(1)"></svg>', b'<html>not an image</html>'):
            with self.assertRaises(Invalid):
                self.service.upload(self.ws,self.cid,self.actor,{'name':'fake.png','body':base64.b64encode(content).decode()})
        data={'name':'real.png','body':base64.b64encode(PNG).decode()}
        self.service.upload(self.ws,self.cid,self.actor,data)
        with self.assertRaises(Invalid):self.service.upload(self.ws,self.cid,self.actor,data)

    def test_metrics_validation_and_zero_denominator(self):
        self.package()
        m={'platform':'x','period':'First day','provenance':'X native analytics','impressions':0,'likes':0,'comments':0,'shares':0,'saves':0}
        with self.assertRaises(Invalid):self.service.metrics(self.ws,self.cid,self.actor,m)
        self.service.publication(self.ws,self.cid,self.actor,{'platform':'x','url':'https://x.com/example/status/1','confirmed':True})
        with self.assertRaises(Invalid):self.service.metrics(self.ws,self.cid,self.actor,{**m,'likes':-1})
        self.service.metrics(self.ws,self.cid,self.actor,m)
        self.worker.tick()
        self.assertIsNone(self.doc()['analysis']['rows'][0]['engagement_rate'])

    def test_future_brief_includes_traceable_reflections(self):
        self.package()
        self.service.publication(self.ws,self.cid,self.actor,{'platform':'x','url':'https://x.com/example/status/1','confirmed':True})
        self.service.metrics(self.ws,self.cid,self.actor,{'platform':'x','period':'First day','provenance':'Fixture measurement','impressions':100,'likes':5,'comments':2,'shares':1,'saves':3,'comment_notes':'Two fixture comments mention the composition. Not representative.'})
        self.worker.tick()
        self.assertEqual(len(self.doc()['analysis']['comment_notes']),1)
        other=self.service.create(self.ws,self.actor,{'title':'Next study','source':'https://example.org/next','source_date':'2026-10-01','evidence':'Another test fixture','priority':50})
        self.worker.tick()
        self.service.task(self.ws,other,{'kind':'creative','key':'next-brief'})
        self.worker.tick()
        doc=next(c for c in self.service.snapshot(self.ws)['campaigns'] if c['id']==other)['document']
        self.assertEqual(doc['brief']['prior_reflections'][0]['campaign'],self.cid)
        self.assertIn('hypotheses to test',doc['brief']['prompt'])

    def test_url_and_date_validation(self):
        for url in ('javascript:alert(1)','https://user:pass@example.com/','file:///etc/passwd'):
            with self.assertRaises(Invalid):self.service.create(self.ws,self.actor,{'title':'Test','source':url,'source_date':'2026-10-01','evidence':'Test evidence','priority':50})


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.server=Server(('127.0.0.1',0),Store(str(Path(cls.tmp.name)/'http.sqlite3')))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.tmp.cleanup()

    def request(self,path,data=None,headers=None):
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json',**(headers or {})})
        try:response=urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:response=e
        self.addCleanup(response.close)
        return response

    def test_auth_csrf_and_membership(self):
        self.assertEqual(self.request('/api/snapshot').status,401)
        response=self.request('/api/register',{'email':'http@example.test','password':'http-password-123','name':'HTTP studio'})
        self.assertEqual(response.status,200)
        csrf=json.load(response)['csrf']
        cookie=response.headers['Set-Cookie'].split(';')[0]
        me=json.load(self.request('/api/me',headers={'Cookie':cookie}))
        headers={'Cookie':cookie,'X-Workspace':me['workspaces'][0]['id']}
        self.assertEqual(self.request('/api/profile',{},headers).status,403)
        self.assertEqual(self.request('/api/snapshot',headers={**headers,'X-Workspace':'other'}).status,403)
        self.assertEqual(self.request('/api/snapshot',headers=headers).status,200)
        self.assertEqual(self.request('/api/logout',{}, {**headers,'X-CSRF-Token':csrf,'Origin':'https://evil.example'}).status,403)
        self.assertEqual(self.request('/api/logout',{}, {**headers,'X-CSRF-Token':csrf}).status,200)
        self.assertEqual(self.request('/api/me',headers=headers).status,401)

    def test_static_headers_and_health(self):
        response=self.request('/')
        self.assertEqual(response.status,200)
        self.assertIn("script-src 'self'",response.headers['Content-Security-Policy'])
        self.assertEqual(self.request('/api/health').status,200)
        self.assertEqual(self.request('/../../README.md').status,404)


if __name__=='__main__':unittest.main()
