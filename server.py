import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).parent
DB = Path(os.environ.get('REVISION_DB', ROOT / 'revision.sqlite3'))
PORT = int(os.environ.get('PORT', '8000'))
ON_RENDER = os.environ.get('RENDER') == 'true'
HOST = os.environ.get('HOST', '0.0.0.0' if ON_RENDER else '127.0.0.1')
APP_ORIGIN = os.environ.get('APP_ORIGIN', os.environ.get('RENDER_EXTERNAL_URL', '')).rstrip('/')
SECURE_COOKIE = '; Secure' if ON_RENDER or APP_ORIGIN.startswith('https://') else ''

QUESTIONS = [
 ('Memory', 'Multi-store model', 'Describe the three stores in the multi-store model of memory.', [('Sensory register briefly holds sensory information.', ['sensory']), ('Short-term memory has limited capacity and duration.', ['short-term', 'short term', 'stm']), ('Long-term memory can retain information for extended periods.', ['long-term', 'long term', 'ltm'])]),
 ('Memory', 'Working memory', 'Explain the role of the central executive in working memory.', [('It directs attention.', ['attention', 'focus']), ('It coordinates the other components and allocates resources.', ['coordinat', 'allocat', 'control'])]),
 ('Memory', 'Retrieval', 'Explain the difference between recall and recognition.', [('Recall produces information without the target being presented.', ['produc', 'generat', 'without', 'retrieve']), ('Recognition identifies previously encountered information.', ['identif', 'previous', 'familiar'])]),
 ('Social Influence', 'Conformity', 'Distinguish normative from informational social influence.', [('Normative influence involves a desire for acceptance or avoiding rejection.', ['accept', 'reject', 'fit in', 'liked']), ('Informational influence involves looking to others for the correct answer.', ['correct', 'right', 'uncertain'])]),
 ('Social Influence', 'Obedience', 'What is obedience, and how does it differ from conformity?', [('Obedience follows a direct instruction from an authority.', ['authorit']), ('Conformity involves adapting to group pressure or norms.', ['group', 'norm', 'peer'])]),
 ('Social Influence', 'Minority influence', 'Explain why consistency can help a minority influence a majority.', [('Consistency shows a stable position over time or between members.', ['stable', 'time', 'same', 'agree']), ('It can encourage others to reconsider their views.', ['reconsider', 'think', 'question', 'reflect'])]),
 ('Attachment', 'Attachment behaviours', 'Describe two behaviours that can indicate an infant attachment.', [('Proximity seeking involves staying close to the caregiver.', ['close', 'proximity']), ('Separation distress involves becoming upset when the caregiver leaves.', ['distress', 'upset', 'separat'])]),
 ('Attachment', 'Internal working model', 'What is an internal working model of attachment?', [('It is a mental representation or expectation of relationships.', ['mental', 'expect', 'represent']), ('It develops from early interactions with a caregiver.', ['early', 'caregiver', 'parent']), ('It may influence later relationships.', ['later', 'future'])]),
 ('Attachment', 'Research evaluation', 'Give two reasons to be cautious when generalising attachment research.', [('Cultural differences can affect behaviour and its interpretation.', ['cultur']), ('A limited or unrepresentative sample can restrict generalisation.', ['sample', 'represent'])]),
 ('Biopsychology', 'Neurons', 'Describe the roles of dendrites, the axon and terminal buttons.', [('Dendrites receive signals.', ['dendrit']), ('The axon carries impulses away from the cell body.', ['axon']), ('Terminal buttons release neurotransmitters.', ['neurotransmit'])]),
 ('Biopsychology', 'Synaptic transmission', 'Outline how a signal crosses a chemical synapse.', [('Neurotransmitters are released from the presynaptic neuron.', ['release']), ('They diffuse across the synaptic gap.', ['diffus', 'gap', 'cleft']), ('They bind to receptors on the postsynaptic membrane.', ['receptor', 'bind'])]),
 ('Biopsychology', 'Nervous system', 'Distinguish the central and peripheral nervous systems.', [('The central nervous system includes the brain and spinal cord.', ['brain']), ('The peripheral nervous system connects the CNS to the rest of the body.', ['body', 'outside', 'connect'])]),
 ('Research Methods', 'Experimental variables', 'Explain independent and dependent variables in an experiment.', [('The independent variable is manipulated by the researcher.', ['manipulat', 'change']), ('The dependent variable is measured as the outcome.', ['measur', 'outcome'])]),
 ('Research Methods', 'Reliability and validity', 'Distinguish reliability from validity.', [('Reliability concerns consistency or repeatability.', ['consisten', 'repeat']), ('Validity concerns whether a measure captures what it intends to measure.', ['intend', 'accur', 'supposed'])]),
 ('Research Methods', 'Ethics', 'Explain informed consent and the right to withdraw.', [('Informed consent requires sufficient information to agree voluntarily.', ['inform', 'voluntar']), ('Participants can leave a study without penalty.', ['leave', 'withdraw', 'penalt'])]),
]

class DatabaseConnection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect():
    con = sqlite3.connect(DB, timeout=15, factory=DatabaseConnection)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    return con

def init():
    admin_password = os.environ.get('ADMIN_PASSWORD', '')
    if ON_RENDER and not admin_password:
        raise ValueError('Set ADMIN_PASSWORD in Render before starting the service.')
    if admin_password and not 10 <= len(admin_password) <= 128:
        raise ValueError('ADMIN_PASSWORD must contain 10–128 characters.')
    if ON_RENDER and not APP_ORIGIN.startswith('https://'):
        raise ValueError('Set APP_ORIGIN to the HTTPS website URL.')
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER REFERENCES users(id), expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, user_id INTEGER REFERENCES users(id), question_id INTEGER NOT NULL, answer TEXT NOT NULL, confidence INTEGER NOT NULL, score REAL NOT NULL, matched TEXT NOT NULL, reviewed INTEGER DEFAULT 0, created REAL NOT NULL);
        ''')
        columns = {row['name'] for row in con.execute('PRAGMA table_info(users)')}
        if 'role' not in columns:
            con.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")
        con.execute("UPDATE users SET email='admin@admin.com' WHERE email='admin' AND role='admin'")
        if admin_password:
            admin = con.execute("SELECT * FROM users WHERE email='admin@admin.com'").fetchone()
            if admin and admin['role'] != 'admin':
                raise ValueError('The admin email is already registered as a student.')
            if not admin or not hmac.compare_digest(admin['password'], password_hash(admin_password, admin['salt'])):
                salt = secrets.token_hex(16)
                hashed = password_hash(admin_password, salt)
                if admin:
                    con.execute('UPDATE users SET salt=?,password=? WHERE id=?', (salt, hashed, admin['id']))
                    con.execute('DELETE FROM sessions WHERE user_id=?', (admin['id'],))
                else:
                    con.execute('INSERT INTO users(name,email,salt,password,role) VALUES(?,?,?,?,?)',
                                ('Admin', 'admin@admin.com', salt, hashed, 'admin'))

def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()

class Handler(SimpleHTTPRequestHandler):
    scheme = 'http'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'public'), **kwargs)

    def send_json(self, value, status=200, cookie=None):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        if cookie:
            secure = SECURE_COOKIE or ('; Secure' if self.scheme == 'https' else '')
            self.send_header('Set-Cookie', cookie + secure)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def token(self):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get('Cookie', ''))
            return cookie['session'].value if 'session' in cookie else ''
        except Exception:
            return ''

    def user(self, con):
        return con.execute('SELECT users.id,name,email,role FROM users JOIN sessions ON users.id=sessions.user_id WHERE token=? AND expires>?', (hashlib.sha256(self.token().encode()).hexdigest(), time.time())).fetchone()

    def do_GET(self):
        if self.path == '/health':
            with connect() as con:
                con.execute('SELECT 1 FROM users LIMIT 1')
            return self.send_json({'status': 'ok'})
        if not self.path.startswith('/api/'):
            return super().do_GET()
        with connect() as con:
            user = self.user(con)
            if self.path == '/api/me':
                return self.send_json(dict(user) if user else None)
            if not user:
                return self.send_json({'error': 'Please log in first.'}, 401)
            if self.path == '/api/admin':
                if user['role'] != 'admin':
                    return self.send_json({'error': 'Administrator access required.'}, 403)
                students = [dict(row) for row in con.execute("SELECT id,name,email FROM users WHERE role='student' ORDER BY name,id")]
                attempts = [dict(row) for row in con.execute("SELECT attempts.* FROM attempts JOIN users ON users.id=attempts.user_id WHERE users.role='student' ORDER BY created DESC,attempts.id DESC")]
                return self.send_json({'students': students, 'attempts': attempts})
            if self.path == '/api/data':
                questions = [{'id': i, 'topic': q[0], 'subtopic': q[1], 'prompt': q[2]} for i, q in enumerate(QUESTIONS)]
                attempts = [dict(row) for row in con.execute('SELECT * FROM attempts WHERE user_id=? ORDER BY created DESC,id DESC', (user['id'],))]
                return self.send_json({'questions': questions, 'attempts': attempts})
            return self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        origin = self.headers.get('Origin')
        expected_origin = APP_ORIGIN or self.scheme + '://' + self.headers.get('Host', '')
        if origin and origin != expected_origin:
            return self.send_json({'error': 'Invalid origin'}, 403)
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 20000:
                raise ValueError('Invalid request size.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Expected a JSON object.')
            with connect() as con:
                if self.path in ('/api/register', '/api/login'):
                    email = str(data.get('email', '')).strip().lower()
                    password = str(data.get('password', ''))
                    admin_login = self.path == '/api/login' and email == 'admin@admin.com'
                    if not admin_login and (not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or len(email) > 254 or not 10 <= len(password) <= 128):
                        raise ValueError('Use a valid email and a password of 10–128 characters.')
                    if not 1 <= len(password) <= 128:
                        raise ValueError('Enter your password.')
                    if self.path == '/api/register':
                        name = str(data.get('name', '')).strip()
                        if not 1 <= len(name) <= 60:
                            raise ValueError('Enter a name of 1–60 characters.')
                        salt = secrets.token_hex(16)
                        try:
                            cursor = con.execute('INSERT INTO users(name,email,salt,password) VALUES(?,?,?,?)', (name, email, salt, password_hash(password, salt)))
                        except sqlite3.IntegrityError:
                            raise ValueError('This email already has an account. Please log in.')
                        user_id = cursor.lastrowid
                    else:
                        row = con.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
                        salt = row['salt'] if row else '00' * 16
                        hashed = password_hash(password, salt)
                        if not row or not hmac.compare_digest(row['password'], hashed):
                            return self.send_json({'error': 'Email or password is incorrect.'}, 401)
                        user_id = row['id']
                    token = secrets.token_urlsafe(32)
                    con.execute('INSERT INTO sessions VALUES(?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time() + 604800))
                    con.commit()
                    return self.send_json({'ok': True}, cookie=f'session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=604800')
                user = self.user(con)
                if not user:
                    return self.send_json({'error': 'Please log in first.'}, 401)
                if self.path == '/api/logout':
                    con.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(self.token().encode()).hexdigest(),))
                    con.commit()
                    return self.send_json({'ok': True}, cookie='session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                if self.path == '/api/answer':
                    qid = data.get('question_id')
                    confidence = data.get('confidence', 2)
                    answer = str(data.get('answer', '')).strip()
                    if type(qid) is not int or not 0 <= qid < len(QUESTIONS) or confidence not in (1, 2, 3) or len(answer) > 5000:
                        raise ValueError('Invalid answer.')
                    q = QUESTIONS[qid]
                    matched = [any(term in answer.lower() for term in terms) for _, terms in q[3]]
                    score = sum(matched) / len(matched)
                    cursor = con.execute('INSERT INTO attempts(user_id,question_id,answer,confidence,score,matched,created) VALUES(?,?,?,?,?,?,?)', (user['id'], qid, answer, confidence, score, json.dumps(matched), time.time()))
                    con.commit()
                    return self.send_json({'id': cursor.lastrowid, 'points': [p[0] for p in q[3]], 'matched': matched, 'score': score})
                if self.path == '/api/review':
                    row = con.execute('SELECT * FROM attempts WHERE id=? AND user_id=?', (data.get('id'), user['id'])).fetchone()
                    if not row:
                        return self.send_json({'error': 'Answer not found.'}, 404)
                    matched = data.get('matched')
                    if not isinstance(matched, list) or len(matched) != len(QUESTIONS[row['question_id']][3]) or any(type(v) is not bool for v in matched):
                        raise ValueError('Invalid review.')
                    con.execute('UPDATE attempts SET score=?,matched=?,reviewed=1 WHERE id=?', (sum(matched) / len(matched), json.dumps(matched), row['id']))
                    con.commit()
                    return self.send_json({'ok': True})
                return self.send_json({'error': 'Not found'}, 404)
        except (ValueError, TypeError, json.JSONDecodeError) as error:
            self.send_json({'error': str(error)}, 400)

if __name__ == '__main__':
    init()
    print(f'Recall is listening on {HOST}:{PORT}', flush=True)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
