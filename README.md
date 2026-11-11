# Recall — local Psychology retrieval practice

Run `python server.py`, then open http://localhost:8000.

Python 3.10+ is required. No third-party Python packages are needed. Locally, the server binds only to this computer; on Render it binds to 0.0.0.0. Stop it with Ctrl+C.

Accounts, hashed passwords, login sessions and answer history are stored in revision.sqlite3. Keep this file private and back it up to retain student records. Register through the website. Sessions last seven days and logout revokes the session.

The starter bank includes 15 original questions across Memory, Social Influence, Attachment, Biopsychology and Research Methods. It is board-independent foundational practice, not complete syllabus coverage. A teacher should review content before classroom use.

Assessment uses versioned, conservative checks against original practice-rubric points. Each point requires linked concepts in a clause. Students receive evidence snippets and guiding questions for missed points. Automated results remain provisional and non-empty answers enter the teacher queue. No AI service is connected. These rules can miss paraphrases or misinterpret answers; teacher judgement remains necessary. Percentages show answer-point coverage rather than exam grades. Existing historical scores are preserved and labelled as legacy.

## PythonAnywhere (WSGI)

1. Upload or clone this project into your PythonAnywhere home folder.
2. In **Web > Add a new web app**, choose **Manual configuration** and Python 3.10 or newer.
3. Open the **WSGI configuration file** linked in the Web tab. Replace its contents with `pythonanywhere_wsgi.example.py` from this project.
4. In that configuration, replace YOUR_USERNAME, the project folder path, the exact HTTPS site URL, and ADMIN_PASSWORD. Use the domain shown in your Web tab (including the EU domain if applicable). Keep your real password out of Git.
5. Click **Reload** in the Web tab. Enable **Force HTTPS**. Open your site and `/health` to verify startup, then register a student account or log in as `admin@admin.com` with your chosen password.

No build command, start command, virtualenv, or third-party dependencies are required. PythonAnywhere imports `application` from `wsgi.py`; do not run `python server.py` in a console to host the site. The WSGI app serves the files in `public/` itself, so static file mappings are optional. Never map the repository root or database folder as a static directory.

SQLite is stored at `/home/YOUR_USERNAME/recall-data/revision.sqlite3`, outside the code folder and public files. The parent directory is created on startup. Do not use Render's `/var/data` path here. Keep a backup before replacing or migrating an existing database; this setup creates an empty database when none exists. Reloading the app reuses the configured database.

For local WSGI checks, run `python -m unittest discover -s tests -v`. The `wsgi_app.py` transport shares the API handlers with the original server and supports GET, HEAD and POST. `wsgi.py` initializes the database once when each worker imports it. Configure environment variables before importing it.

Official setup guide: https://help.pythonanywhere.com/pages/WebAppBasics/

## Render web service

Use Python 3, leave Root Directory blank, and set:

- Build Command: `python -m py_compile server.py`
- Start Command: `python server.py`
- Health Check Path: `/health`

For persistent SQLite storage, use a paid web service and add a disk (1 GB is ample to start) mounted at `/var/data`. Set these environment variables:

| Variable | Value |
| --- | --- |
| `REVISION_DB` | `/var/data/revision.sqlite3` |
| `ADMIN_PASSWORD` | Your own password, 10–128 characters |
| `APP_ORIGIN` | Your exact HTTPS site URL, without a trailing slash |

APP_ORIGIN may be omitted for the default Render URL: the app uses Render's RENDER_EXTERNAL_URL automatically. Set it explicitly when using a custom domain; use that domain consistently when logging in. Render supplies PORT and RENDER automatically.

Log in as `admin@admin.com` with ADMIN_PASSWORD. Changing ADMIN_PASSWORD and restarting updates the administrator password and revokes existing admin sessions. No default administrator password is created. For local admin access, set ADMIN_PASSWORD before starting too.

Only files under the disk mount survive redeploys/restarts. Free Render services cannot attach disks; durable storage on a free web service requires moving to an external database and changing the application. Use a single service instance with SQLite. The disk starts empty: existing local accounts are not uploaded automatically. Never commit revision.sqlite3 or passwords.

Render terminates HTTPS. The application checks browser request origins and marks hosted session cookies Secure. This remains a small prototype using Python's built-in HTTP server, without account recovery, email verification, or login rate limiting.

## Verification

Run `python -m unittest discover -s tests -v` and `python -m py_compile server.py`.

## ECC project skills

ECC deployment-patterns and verification-loop are installed in `.agents/skills`, the project skill location supported by Codex. They are instructions used by the coding assistant, not a server or website dependency. Source: affaan-m/ECC, commit b38be6a7f6350964d59328b52f0624e1d1d552d1 (v2.2.3). Their complete SKILL.md files are local, so use does not depend on reading the OneDrive-backed `.ecc-source` checkout. This does not enable the full ECC plugin's optional hooks or MCP servers.

## V2 learning feedback

The administrator can review each answer point, add a required feedback note and save a final teacher mark. Changes are recorded in `marking_audit`, including old/new point decisions, teacher identity and timestamp. A version check prevents a stale browser overwriting a newer decision. Student requests cannot change V2 marks. Old scores are preserved during automatic additive database migration; back up the database before deployment.

Questions scoring below 80% are scheduled three days after their most recent attempt. The dashboard and portfolio show upcoming/due questions with a direct re-attempt button. Early practice remains available. Progress compares the first answer with the latest answer at least three days later on the same question. A dash indicates no spaced comparison yet, rather than an apparent zero gain. This descriptive comparison does not establish that the intervention caused improvement.

Confidence ratings map to 25%, 60% and 90%. Differences of at least 30 percentage points are shown for reflection. Admin cards flag possible overconfidence, due re-attempts and no practice in seven days (including accounts with no answers). These thresholds are prototype design choices and the interface labels provisional marking evidence.

Email summaries and reminders are excluded at the user's request. All next steps are available in the website. No scheduler or email credentials are required.

For PythonAnywhere, upload `learning.py` alongside the updated `server.py` and `public/` files, then reload the web app. The configured database is migrated on startup. Existing account and attempt records are retained.
