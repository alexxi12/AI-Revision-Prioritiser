import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import server


class HostingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = patch.dict(os.environ, {'ADMIN_PASSWORD': 'test-password-123'})
        self.env.start()
        self.addCleanup(self.env.stop)
        for name, value in {'DB': Path(self.temp.name) / 'storage' / 'revision.sqlite3',
                            'APP_ORIGIN': 'https://example.onrender.com',
                            'ON_RENDER': True, 'SECURE_COOKIE': '; Secure'}.items():
            patcher = patch.object(server, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        server.init()
        self.start_server()

    def start_server(self):
        self.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.http.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)

    def stop_server(self):
        if self.http:
            self.http.shutdown()
            self.http.server_close()
            self.thread.join()
            self.http = None

    def request(self, path, body=None, cookie=None, origin='https://example.onrender.com'):
        conn = http.client.HTTPConnection('127.0.0.1', self.http.server_port)
        headers = {'Origin': origin}
        if cookie:
            headers['Cookie'] = cookie
        conn.request('POST' if body is not None else 'GET', path,
                     json.dumps(body) if body is not None else None, headers)
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), json.loads(response.read())
        conn.close()
        return result

    def test_student_history_survives_restart(self):
        status, headers, _ = self.request('/api/register', {'name': 'Student', 'email': 'student@example.com', 'password': 'student-password'})
        self.assertEqual(status, 200)
        self.assertIn('; Secure', headers['Set-Cookie'])
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('/api/admin', cookie=cookie)[0], 403)
        self.assertEqual(self.request('/api/answer', {'question_id': 0, 'answer': 'sensory short-term long-term', 'confidence': 2}, cookie)[0], 200)
        self.stop_server()
        server.init()
        self.start_server()
        self.assertEqual(len(self.request('/api/data', cookie=cookie)[2]['attempts']), 1)
        self.assertEqual(self.request('/health')[0], 200)

    def test_origin_and_json_validation(self):
        self.assertEqual(self.request('/api/login', {}, origin='https://evil.example')[0], 403)
        self.assertEqual(self.request('/api/login', [])[0], 400)

    def test_admin_password_rotation_revokes_sessions(self):
        status, headers, _ = self.request('/api/login', {'email': 'admin@admin.com', 'password': 'test-password-123'})
        self.assertEqual(status, 200)
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.request('/api/admin', cookie=cookie)[0], 200)
        with patch.dict(os.environ, {'ADMIN_PASSWORD': 'new-password-456'}):
            server.init()
        self.assertEqual(self.request('/api/admin', cookie=cookie)[0], 401)
        self.assertEqual(self.request('/api/login', {'email': 'admin@admin.com', 'password': 'test-password-123'})[0], 401)
        self.assertEqual(self.request('/api/login', {'email': 'admin@admin.com', 'password': 'new-password-456'})[0], 200)

    def test_render_requires_admin_password(self):
        with patch.dict(os.environ, {'ADMIN_PASSWORD': ''}):
            with self.assertRaisesRegex(ValueError, 'ADMIN_PASSWORD'):
                server.init()

    def test_render_binding_and_local_defaults(self):
        for render, host in [('true', '0.0.0.0'), ('false', '127.0.0.1')]:
            env = dict(os.environ, RENDER=render, PORT='12345')
            env.pop('HOST', None)
            result = subprocess.check_output([sys.executable, '-c', 'import server; print(server.HOST, server.PORT)'], env=env, text=True)
            self.assertEqual(result.strip(), host + ' 12345')


if __name__ == '__main__':
    unittest.main()
