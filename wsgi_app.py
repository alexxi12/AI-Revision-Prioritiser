"""WSGI transport for Recall's existing request handlers; no listening socket."""

from email.message import Message
from http import HTTPStatus
from io import BytesIO
import mimetypes

import server


class WSGIHandler(server.Handler):
    """Adapt request streams and response headers, sharing all API logic."""

    def __init__(self, environ):
        self.command = environ['REQUEST_METHOD'].upper()
        self.path = environ.get('PATH_INFO', '/') or '/'
        self.scheme = environ.get('wsgi.url_scheme', 'http')
        self.headers = Message()
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                self.headers[key[5:].replace('_', '-')] = value
        for key in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            if environ.get(key):
                self.headers[key.replace('_', '-')] = environ[key]
        self.rfile = environ['wsgi.input']
        self.wfile = BytesIO()
        self.status = HTTPStatus.OK
        self.response_headers = []

    def send_response(self, code, message=None):
        self.status = HTTPStatus(code)

    def send_header(self, keyword, value):
        self.response_headers.append((keyword, str(value)))

    def end_headers(self):
        pass

    def static_file(self):
        public = (server.ROOT / 'public').resolve()
        target = (public / self.path.lstrip('/')).resolve()
        if not target.is_relative_to(public):
            return self.send_json({'error': 'Not found'}, 404)
        if target.is_dir():
            target = (target / 'index.html').resolve()
        if not target.is_relative_to(public) or not target.is_file():
            return self.send_json({'error': 'Not found'}, 404)
        body = target.read_bytes()
        content_type = mimetypes.guess_type(str(target))[0] or 'application/octet-stream'
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(body))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.wfile.write(body)

    def dispatch(self):
        if self.command in ('GET', 'HEAD'):
            if self.path == '/health' or self.path.startswith('/api/'):
                self.do_GET()
            else:
                self.static_file()
        elif self.command == 'POST':
            self.do_POST()
        else:
            self.send_json({'error': 'Method not allowed'}, 405)
            self.send_header('Allow', 'GET, HEAD, POST')


def application(environ, start_response):
    handler = WSGIHandler(environ)
    handler.dispatch()
    start_response(f'{handler.status.value} {handler.status.phrase}', handler.response_headers)
    return [b'' if handler.command == 'HEAD' else handler.wfile.getvalue()]
