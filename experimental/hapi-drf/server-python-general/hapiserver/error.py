import logging
logger = logging.getLogger(__name__)

def error(error, config, message=None):
  import json
  if isinstance(error, int):
    error = _hapi_error(error, message=message)

  if 'message' not in error:
    message = _hapi_error(error['code'])['message']

  if 'exception' in error:
    if 'message_console' in error:
      logger.error(f"{error['message_console']}: {error['exception']}")
    else:
      logger.error(f"{message}: {error['exception']}")
  else:
    if 'message_console' in error:
      logger.error(f"{error['message_console']}")
    else:
      logger.error(f"{message}")

  content = {
    "status": {
      "code": error['code'],
      "message": message
    }
  }

  if error['code'] >= 1400 and error['code'] <= 1499:
    status_code = 400
  if error['code'] >= 1500 and error['code'] <= 1599:
    status_code = 500
  if error['code'] == 1500:
    status_code = 500
  if error['code'] == 1501:
    status_code = 501

  response = {
    "status_code": status_code,
    "content": json.dumps(content, indent=2),
    "media_type": "application/json",
  }

  return response


def _hapi_error(code, message=None):
  errors = {
    1200: {"status":{"code": 1200, "message": "OK"}},
    1201: {"status":{"code": 1201, "message": "OK - no data for time range"}},
    1400: {"status":{"code": 1400, "message": "Bad request - user input error"}},
    1401: {"status":{"code": 1401, "message": "Bad request - unknown API parameter name"}},
    1402: {"status":{"code": 1402, "message": "Bad request - syntax error in start time"}},
    1403: {"status":{"code": 1403, "message": "Bad request - syntax error in stop time"}},
    1404: {"status":{"code": 1404, "message": "Bad request - start equal to or after stop"}},
    1405: {"status":{"code": 1405, "message": "Bad request - start < startDate and/or stop > stopDate"}},
    1406: {"status":{"code": 1406, "message": "Bad request - unknown dataset id"}},
    1407: {"status":{"code": 1407, "message": "Bad request - unknown dataset parameter"}},
    1408: {"status":{"code": 1408, "message": "Bad request - too much time or data requested"}},
    1409: {"status":{"code": 1409, "message": "Bad request - unsupported output format"}},
    1410: {"status":{"code": 1410, "message": "Bad request - unsupported include value"}},
    1411: {"status":{"code": 1411, "message": "Bad request - out-of-order or duplicate parameters"}},
    1412: {"status":{"code": 1412, "message": "Bad request - unsupported resolve_references value"}},
    1413: {"status":{"code": 1413, "message": "Bad request - unsupported depth value"}},
    1500: {"status":{"code": 1500, "message": "Internal server error"}},
    1501: {"status":{"code": 1501, "message": "Internal server error - upstream request error"}}
  }

  if message is not None:
    # Augment the standard message with the provided one
    errors[code]['status']['message'] += f". {message}"

  return errors.get(code, errors[1500])['status']
