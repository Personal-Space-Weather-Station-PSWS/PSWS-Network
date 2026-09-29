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
  print ("wsgi clean start")
except Exception:
  print ("wsgi exception")
  if  'mod_wsgi' in sys.modules:
    traceback.print_exc()
    os.kill(os.getpid(), signal.SIGINT)
    time.sleep(2.5)
