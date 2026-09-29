openapi_spec = None

def load_openapi_docs():
  """Load OpenAPI documentation from misc/openapi.json"""
  import os
  import json
  import logging

  global openapi_spec

  logger = logging.getLogger(__name__)

  try:
    # Get the path relative to the hapiserver module
    base_dir = os.path.dirname(os.path.abspath(__file__))
    openapi_path = os.path.join(base_dir, 'openapi.json')

    with open(openapi_path, 'r') as f:
      openapi_spec = json.load(f)

  except Exception as e:
    emsg = f"Could not load OpenAPI documentation from {openapi_path}: {e}"
    emsg += "\nExiting with code 1."
    logger.error(emsg)
    exit(1)

def kwargs(path):
  """Extract documentation from OpenAPI spec"""

  docs = get(path)

  if path[-1] in ['get', 'head']:
    return {
        'tags': docs.get('tags', []),
        'summary': docs.get('summary', ''),
        'description': docs.get('description', '')
    }

  if path[0] == 'info' and len(path) == 1:
    return {
          'title': docs['title'],
          'description': docs['description'],
          'contact': docs['contact'],
          'license': docs['license'],
          'docs_url': docs.get('docs_url', '/docs'),
          'redoc_url': docs.get('redoc_url', '/redoc'),
          'openapi_url': docs.get('openapi_url', '/openapi.json')
  }

  return {}

def get(path, kwargs=None):
  """Extract documentation from OpenAPI spec"""
  import copy

  if openapi_spec is None:
    load_openapi_docs()

  spec = copy.deepcopy(openapi_spec)
  if isinstance(path, (list, tuple)):
    node = spec.copy()
    for key in path:
      if isinstance(node, dict):
        node = node.get(key, {})
      elif isinstance(node, list) and isinstance(key, int) and 0 <= key < len(node):
        node = node[key]
      else:
        node = {}
        break

    if 'parameters' in node:
      parameters = {}
      for parameter in node['parameters']:
        parameters[parameter['name']] = parameter
      node['parameters'] = parameters

    return node