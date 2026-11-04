from io import BytesIO
import json
import os
import subprocess
import sys
from wsgiref.util import setup_testing_defaults
from wsgiref.validate import validator
from unittest.mock import patch

import test_hosting
import server
from wsgi_app import application


class WSGITests(test_hosting.HostingTests):
    # Run the same authentication and persistence checks through real WSGI calls.
    def start_server(self):
        pass

    def stop_server(self):
        pass

    def raw_request(self, path, body=None, cookie=None,
                    origin='https://example.onrender.com', method=None):
        environ = {}
        setup_testing_defaults(environ)
        payload = json.dumps(body).encode() if body is not None else b''
        environ.update({
            'REQUEST_METHOD': method or ('POST' if body is not None else 'GET'),
            'PATH_INFO': path,
            'QUERY_STRING': '',
            'HTTP_HOST': 'example.onrender.com',
            'HTTP_ORIGIN': origin,
            'CONTENT_LENGTH': str(len(payload)),
            'CONTENT_TYPE': 'application/json',
            'wsgi.url_scheme': 'https',
            'wsgi.input': BytesIO(payload),
        })
        if cookie:
            environ['HTTP_COOKIE'] = cookie
        captured = {}

        def start_response(status, headers, exc_info=None):
            captured.update(status=int(status.split()[0]), headers=dict(headers))

        response = validator(application)(environ, start_response)
        try:
            content = b''.join(response)
        finally:
            response.close()
        return captured['status'], captured['headers'], content

    def request(self, path, body=None, cookie=None, origin='https://example.onrender.com'):
        status, headers, content = self.raw_request(path, body, cookie, origin)
        return status, headers, json.loads(content)

    def test_static_files_and_head(self):
        status, headers, content = self.raw_request('/')
        self.assertEqual(status, 200)
        self.assertIn(b'<html', content.lower())
        self.assertEqual(headers['Content-Type'], 'text/html')
        self.assertEqual(self.raw_request('/app.js')[0], 200)
        status, head_headers, content = self.raw_request('/', method='HEAD')
        self.assertEqual(status, 200)
        self.assertEqual(head_headers['Content-Length'], headers['Content-Length'])
        self.assertEqual(content, b'')
        self.assertEqual(self.raw_request('/health', method='HEAD')[2], b'')

    def test_https_without_render_configuration(self):
        with patch.object(server, 'APP_ORIGIN', ''), patch.object(server, 'SECURE_COOKIE', ''), patch.object(server, 'ON_RENDER', False):
            status, headers, _ = self.request('/api/login', {'email': 'admin@admin.com', 'password': 'test-password-123'})
            self.assertEqual(status, 200)
            self.assertIn('; Secure', headers['Set-Cookie'])

    def test_private_files_and_unsupported_methods(self):
        for path in ('/../server.py', '/../revision.sqlite3', '/missing', '/server.py'):
            self.assertEqual(self.raw_request(path)[0], 404)
        status, headers, _ = self.raw_request('/', method='DELETE')
        self.assertEqual(status, 405)
        self.assertEqual(headers['Allow'], 'GET, HEAD, POST')

    def test_entry_point_initializes_database_without_listening(self):
        env = dict(os.environ, RENDER='false', APP_ORIGIN='https://student.pythonanywhere.com',
                   REVISION_DB=str(self.temp.name + '/wsgi-data/revision.sqlite3'))
        subprocess.run([sys.executable, '-c',
                        'import wsgi; assert callable(wsgi.application); '
                        'import server; assert server.DB.is_file()'],
                       env=env, check=True, timeout=10)
