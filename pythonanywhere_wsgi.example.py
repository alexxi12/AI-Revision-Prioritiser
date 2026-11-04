"""Copy into the WSGI configuration file linked from PythonAnywhere's Web tab.

Replace YOUR_USERNAME and the project directory with your actual paths.
Edit the password only in PythonAnywhere's private WSGI config, not this repo.
"""

import os
import sys

project = '/home/YOUR_USERNAME/AI-Revision-Prioritiser'
sys.path.insert(0, project)

os.environ['APP_ORIGIN'] = 'https://YOUR_USERNAME.pythonanywhere.com'
os.environ['REVISION_DB'] = '/home/YOUR_USERNAME/recall-data/revision.sqlite3'
os.environ['ADMIN_PASSWORD'] = 'REPLACE_WITH_YOUR_OWN_PASSWORD'
if os.environ['ADMIN_PASSWORD'] == 'REPLACE_WITH_YOUR_OWN_PASSWORD':
    raise ValueError('Set your own ADMIN_PASSWORD in the PythonAnywhere WSGI configuration.')

from wsgi import application  # noqa: E402,F401
