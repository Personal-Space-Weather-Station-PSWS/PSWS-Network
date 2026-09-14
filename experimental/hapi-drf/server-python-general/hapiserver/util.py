import logging
logger = logging.getLogger(__name__)

def set_env(config):
  import os
  for name, value in config.get("ENV", {}).items():
    os.environ[name] = str(value)
    logger.debug(f"Environment variable set: {name}={value}")


def expand_env(config):
  import os
  import re

  regex =r'\$(?:{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)}|(?P<plain>[A-Za-z_][A-Za-z0-9_]*))'
  env_pattern = re.compile(regex)

  def _replace_env(obj):
    if isinstance(obj, dict):
      for k, v in obj.items():
        obj[k] = _replace_env(v)
      return obj
    if isinstance(obj, list):
      return [_replace_env(v) for v in obj]
    if isinstance(obj, tuple):
      return tuple(_replace_env(v) for v in obj)
    if isinstance(obj, str):
      def repl(m):
        name = m.group('braced') or m.group('plain')
        return os.environ.get(name, '')
      return env_pattern.sub(repl, obj)
    return obj

  try:
    _replace_env(config)
  except Exception as e:
    logger.warning(f"Environment variable substitution failed: {e}")


def check_config(config):
  import os

  if not isinstance(config, dict):
    logger.error("Configuration is not a dictionary. Exiting with code 1.")
    exit(1)

  if "about" not in config:
    logger.error("Configuration missing 'about' section. Exiting with code 1.")
    exit(1)

  if "HAPI" not in config['about']:
    logger.error("Configuration 'about' section missing 'HAPI' entry. Exiting with code 1.")
    exit(1)

  fname = config.get("index.html", None)
  if fname is not None:
    fname = os.path.expanduser(fname)
    config['index.html'] = os.path.expanduser(config['index.html'])
    if not os.path.exists(config['index.html']):
      logger.error(f"index.html file not found: '{fname}'")
      exit(1)

  for script_name, script in config.get("scripts", {}).items():
    config['scripts'][script_name] = os.path.expanduser(script)
    if not os.path.exists(config['scripts'][script_name]):
      logger.error(f"Script file for endpoint /{script_name} not found: '{script}'")
      exit(1)

  for endpoint in config.get("scripts", {}):
    if 'functions' in config and endpoint in config['functions']:
      logger.error(f"Both script and function defined for {endpoint} in config.")
      exit(1)
