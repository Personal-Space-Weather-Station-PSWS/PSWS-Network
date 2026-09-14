import sys
import os
import json

def config():

  if hasattr(config, '_cached_instance'):
    return config._cached_instance

  config_file = os.path.join(os.path.dirname(__file__), "..", "config.json")
  if os.path.exists(config_file):
    with open(config_file, 'r') as f:
      try:
        config_all = json.load(f)
      except Exception as e:
        print(f"Error: Could not parse config file: {config_file}: {e}", file=sys.stderr)
        exit(1)
      config_module = config_all['module']
  else:
    print(f"Error: Config file not found: {config_file}", file=sys.stderr)
    exit(1)

  if 'categories' not in config_module:
    config['categories'] = None

  # Default data directory
  data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
  # Override from config
  DATA_DIR = config_module.get('dataDir', data_dir)

  config_module['dataDir'] = os.path.expanduser(DATA_DIR)

  # Memoize config
  config._cached_instance = config_module

  return config_module


def madrigalData(debug=False):
  import madrigalWeb.madrigalWeb

  conf = config()
  url = conf['madrigalUrl']

  if hasattr(madrigalData, '_cached_instance'):
    return madrigalData._cached_instance

  if debug:
    print(f"Calling madrigalWeb.madrigalWeb.MadrigalData('{url})'")
  db = madrigalWeb.madrigalWeb.MadrigalData(url)

  # Memoize instance
  madrigalData._cached_instance = db

  return db


def read_json(file_name, debug=False):
  if debug:
    print(f'Reading {file_name}')
  with open(file_name, 'r') as f:
      data = json.load(f)
  return data


def write_json(file_name, data, debug=False, indent=0):
  indent = indent*" "
  if debug:
    print(f'{indent}Writing {file_name}')
  if not os.path.exists(os.path.dirname(file_name)):
    if debug:
      print(f'{indent}Creating directory: {os.path.dirname(file_name)}')
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
  with open(file_name, 'w') as f:
    json.dump(data, f, indent=2)


def to_dicts(obj):
  return [o.__dict__ for o in obj if o is not None]