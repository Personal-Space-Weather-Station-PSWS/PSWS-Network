# Usage:
#   python info.py <id>
# where <id> is the station ID, e.g., S000028 found in first column of catalog.csv
#
# Examples:
#   python info.py S000028/mag
#   python info.py N000001/doppler

# Returns HAPI info JSON stdout
#
# Equivalent API response to:
#   hapi/info?dataset=<id>

import csv
import json
from pathlib import Path

# Get PSWS_DATA_DIR from environment variable
#PSWS_DATA_DIR = os.getenv("PSWS_DATA_DIR")

SCRIPT_DIR = Path(__file__).resolve().parent

def get_catalog():
  catalog = {}
  file = SCRIPT_DIR / 'catalog.csv'
  with open(file, 'r') as csvfile:
    reader = csv.reader(csvfile)
    for row in reader:
      if row[0].startswith('#'):
        continue
      catalog[row[0].strip()] = {
        'nickname': row[1].strip(),
        'startDateTime': row[2].strip(),
        'stopDateTime': row[3].strip(),
        'lat': float(row[4]),
        'long': float(row[5]),
        'elevation': float(row[6])
      }
  return catalog

def info(dataset):
  catalog = get_catalog()

  data_type = dataset.split('/')[-1]
  with open(SCRIPT_DIR / f'info.{data_type}.template.json', 'r') as f:
    info = json.load(f)

  dataset = sys.argv[1]
  if dataset not in catalog:
    print(f"ID {dataset} not found in catalog", file=sys.stderr)
    sys.exit(1)

  info['startDate'] = catalog[dataset]['startDateTime']
  info['stopDate'] = catalog[dataset]['stopDateTime']
  info['geoLocation'] = [
    catalog[dataset]['lat'],
    catalog[dataset]['long'],
    catalog[dataset]['elevation']
  ]

  return info

if __name__ == "__main__":
  import sys
  print(json.dumps(info(sys.argv[1]), indent=2))
