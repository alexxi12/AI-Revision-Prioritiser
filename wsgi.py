"""Import this module from the host's WSGI configuration after setting env vars."""

from server import init
from wsgi_app import application

init()
