# Usage:
#   python test.py
#
# See
#  python test.py --help
# for configuration options, e.g.,
#  python test.py --config config.json --port 8080

import logging

logger = logging.getLogger(__name__)

def log_test_title(url):
  line = len(url)*"-"
  logger.info(line)
  logger.info(f"Testing {url}")
  logger.info(line)


def run_tests(configs, wait):
  import requests
  import utilrsw.uvicorn

  port = configs['server']['--port']
  url_base = f"http://0.0.0.0:{port}/hapi"

  wait['url'] = url_base

  utilrsw.uvicorn.start('hapiserver.app', configs, wait)


  url = url_base
  log_test_title(url)
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/html' in response.headers['Content-Type']
  assert 'HAPI' in response.text

  url = f"{url_base}/catalog"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'application/json' in response.headers['Content-Type']
  assert 'catalog' in response.json()
  assert len(response.json()['catalog']) > 0

  # Magnetometer data
  url = f"{url_base}/info?dataset=S000028/mag"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'application/json' in response.headers['Content-Type']
  assert 'parameters' in response.json()
  assert len(response.json()['parameters']) > 0

  url = f"{url_base}/data?dataset=S000028/mag&start=2025-10-20T00:00:00Z&stop=2025-10-20T00:00:01Z"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2025-10-20T00:00:00Z')

  # Data extends past stop
  url = f"{url_base}/data?dataset=S000028/mag&start=2025-10-21T04:01:56Z&stop=2025-10-21T04:02:01Z"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2025-10-21T04:01:56Z')

  url = f"{url_base}/data?dataset=S000028/mag&start=2025-10-20T00:00:00Z&stop=2025-10-20T00:00:01Z&parameters=Field_Vector"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2025-10-20T00:00:00Z')

  # Doppler data
  url = f"{url_base}/info?dataset=N000001/doppler"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'application/json' in response.headers['Content-Type']
  assert 'parameters' in response.json()
  assert len(response.json()['parameters']) > 0

  url = f"{url_base}/data?dataset=N000001/doppler&start=2019-05-24T00:07:46Z&stop=2019-05-24T00:07:49Z"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2019-05-24T00:07:46Z')

  url = f"{url_base}/data?dataset=N000001/doppler&start=2019-05-24T00:07:46Z&stop=2019-05-24T00:07:49Z&parameters=Freq"
  response = requests.get(url)
  assert response.status_code == 200
  assert 'text/csv' in response.headers['Content-Type']
  assert response.text.startswith('2019-05-24T00:07:46Z')


if __name__ == "__main__":
  import hapiserver

  wait = {
    "retries": 10,
    "delay": 0.5
  }

  config = "config.json"
  configs = hapiserver.cli(config=config)
  run_tests(configs, wait)
