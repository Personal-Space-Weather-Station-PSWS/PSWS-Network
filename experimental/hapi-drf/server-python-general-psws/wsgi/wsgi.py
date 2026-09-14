# Start new code, part I
def fastapi_app():
  import fastapi
  import a2wsgi

  # FastAPI ASGI app, converted to WSGI
  fastapi_asgi = fastapi.FastAPI()
  @fastapi_asgi.get("/", response_class=fastapi.responses.PlainTextResponse)
  async def hello():
      return "hello world"

  fastapi_wsgi = a2wsgi.ASGIMiddleware(fastapi_asgi)

  return fastapi_wsgi

def combine_apps(fastapi_app, django_app):
  from werkzeug.middleware.dispatcher import DispatcherMiddleware
  # Add /hapi endpoint
  application = DispatcherMiddleware(django_app, {
      "/hapi": fastapi_app
  })
  return application
# End new code, part I


"""
WSGI config for PSWS project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os
from os import sys

import traceback
import signal
import time

# WDE
path = '/var/www/html/PSWS'

print("PYTHON PATH:", sys.executable, sys.path)

if path not in sys.path:
  sys.path.append(path)
path = '/usr/local/lib/python3.6/site-packages'
if path not in sys.path:
  sys.path.append(path)
#path =  '/home/bengelke/.local/lib/python3.6/site-packages'
#if path not in sys.path:
#  sys.path.append(path)
# end WDE


from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PSWS.settings')

try:
  application = get_wsgi_application()
  # Start new code, part II
  application = combine_apps(fastapi_app(), application)
  # End new code, part II
  print ("wsgi clean start")
except Exception:
  print ("wsgi exception")
  if  'mod_wsgi' in sys.modules:
    traceback.print_exc()
    os.kill(os.getpid(), signal.SIGINT)
    time.sleep(2.5)
