__all__ = [
  "app",
  "cli",
  "get",
  "exec",
  "openapi",
  "error",
  "util",
  "run",
  "factory"
]

__version__ = "0.0.1"

from hapiserver import openapi
from hapiserver import util
from hapiserver.cli import cli
from hapiserver.app import app
from hapiserver.exec import exec
from hapiserver.error import error

import logging
logging.basicConfig()

def main():
  # Entry point for console_scripts in setup.py
  import hapiserver
  import utilrsw.uvicorn

  config = hapiserver.cli()

  at = "http://{configs['server']['--host']}:{configs['server']['--port']}/hapi"
  print(f"Starting HAPI server using Uvicorn at {at}")
  utilrsw.uvicorn.run("hapiserver.app", config)
