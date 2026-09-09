# Usage:
#   python data.py <id> <start> <stop>
#   python data.py <id> <start> <stop> <parameters>
#   python data.py <id> <start> <stop> <parameters> <format>
#
# Logical DRF dataset IDs use one catalog entry per station, for example:
#   S000068/drf
#
# A station directory may contain many native Digital RF Observations:
#   $PSWS_DATA_DIR/S000068/OBS2026-08-27T00-01/
#   $PSWS_DATA_DIR/S000068/OBS2026-08-28T00-01/
#   ...
#
# For DRF datasets:
#   format=csv        returns a small manifest (one record per Observation)
#   format=x_drf_zip  returns complete overlapping Observation directory trees
#                     in one ZIP stream. No subchannel extraction or time
#                     slicing is performed inside an Observation.
#
# NOTE: x_drf_zip requires the generic HAPI server to preserve subprocess
# stdout as bytes. The current standard server implementation decodes stdout
# as text and therefore needs the binary-stream enhancement described in the
# accompanying HAPI_SERVER_BINARY_STREAM_PROPOSAL.md.

import csv
import datetime
import json
import os
import re
import sys
import tempfile
import zipfile


debug = False  # Print debug messages to stderr
STREAM_CHUNK_SIZE = 1024 * 1024
OBSERVATION_DURATION = datetime.timedelta(days=1)
OBSERVATION_RE = re.compile(r'^OBS(\d{4}-\d{2}-\d{2}T\d{2}-\d{2})$')


def error(emsg):
  print(f"Error: {emsg}", file=sys.stderr)
  sys.exit(1)


def log(msg):
  if debug:
    print(f"Debug: {msg}", file=sys.stderr)


def _parse_hapi_time(value):
  """Parse a normalized HAPI time such as 2026-08-27T00:01:00Z."""
  try:
    return datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
  except ValueError as exc:
    error(f"Could not parse HAPI time '{value}': {exc}")


def _format_hapi_time(value):
  """Format a UTC datetime as a 20-character HAPI time."""
  value = value.astimezone(datetime.timezone.utc)
  return value.strftime('%Y-%m-%dT%H:%M:%SZ')


def _observation_start(name):
  """Return UTC start time encoded in an OBS... directory name, or None."""
  match = OBSERVATION_RE.match(name)
  if not match:
    return None
  try:
    dt = datetime.datetime.strptime(match.group(1), '%Y-%m-%dT%H-%M')
  except ValueError:
    return None
  return dt.replace(tzinfo=datetime.timezone.utc)


def observations_needed(station_dir, start, stop):
  """Return complete Observation directories overlapping [start, stop)."""
  request_start = _parse_hapi_time(start)
  request_stop = _parse_hapi_time(stop)

  observations = []
  try:
    entries = os.scandir(station_dir)
  except OSError as exc:
    error(f"Could not scan DRF station directory '{station_dir}': {exc}")

  with entries:
    for entry in entries:
      if not entry.is_dir(follow_symlinks=False):
        continue
      obs_start = _observation_start(entry.name)
      if obs_start is None:
        continue
      obs_stop = obs_start + OBSERVATION_DURATION

      # HAPI time selection is [start, stop). Native DRF Observations are
      # indivisible here, so return each complete Observation that overlaps it.
      if obs_start < request_stop and obs_stop > request_start:
        observations.append((obs_start, entry.path))

  observations.sort(key=lambda item: item[0])
  return observations


def files_needed(id, start, stop, data_dir):

  sub_dir_map = {
    'mag': 'magData',
    'doppler': 'csvData',
    'drf': '',
  }

  data_type = id.split('/')[-1]
  if data_type not in sub_dir_map:
    error(
      f"Unknown dataset ID suffix for id '{id}'. "
      "Expected to end with '/mag', '/doppler', or '/drf'."
    )

  # Examples:
  #   S000028/mag      => S000028/magData
  #   S000028/doppler  => S000028/csvData
  #   S000068/drf      => S000068
  dir_base = id.rsplit('/', 1)[0]
  dir_sub = sub_dir_map[data_type]
  dataset_dir = os.path.normpath(os.path.join(data_dir, dir_base, dir_sub))

  if not os.path.exists(dataset_dir):
    error(f"Dataset path does not exist: {dataset_dir}")

  if data_type == 'drf':
    if not os.path.isdir(dataset_dir):
      error(f"DRF station dataset is not a directory: {dataset_dir}")
    return observations_needed(dataset_dir, start, stop)

  # Keep only day precision for existing CSV products.
  start_day = start[0:10]
  stop_day = stop[0:10]

  log(f"Looking for file with data in range [{start_day}, {stop_day}]")

  if data_type == 'mag':
    files = files_needed_mag(dataset_dir, start_day, stop_day)
  else:
    files = files_needed_doppler(dataset_dir, start_day, stop_day)

  if debug:
    if len(files) == 0:
      log(f"No files found with data in range [{start_day}, {stop_day}]")
    else:
      s = "s" if len(files) > 1 else ""
      log(f"Found {len(files)} file{s} with data in range [{start_day}, {stop_day}]")

  return files


def files_needed_doppler(dataset_dir, start, stop):
  files_csv = [f for f in os.listdir(dataset_dir) if f.endswith('.csv')]

  files_needed = []
  for file in sorted(files_csv):
    file_date = file[0:10]
    log(f"File: {file}, date: {file_date}")
    if start <= file_date <= stop:
      files_needed.append(os.path.join(dataset_dir, file))

  return files_needed


def files_needed_mag(dataset_dir, start, stop):
  files_zip = [f for f in os.listdir(dataset_dir) if f.endswith('.zip')]
  files_zip.sort()

  if not files_zip:
    log(f"No .zip files found in dataset directory: {dataset_dir}")
    return []

  log(f"Found {len(files_zip)} files that end with .zip in {dataset_dir}")

  files_needed = []
  for file in files_zip:
    file_date = file[3:13]
    log(f"File: {file}, date: {file_date}")
    if start <= file_date <= stop:
      files_needed.append(os.path.join(dataset_dir, file))

  return files_needed


def print_data(id, files, start, stop, parameters, data_dir, output_format):

  if id.endswith('/mag'):
    if output_format != 'csv':
      error(f"Format '{output_format}' is not supported for magnetometer data")
    for filename in files:
      print_data_mag(filename, start, stop, parameters)
    return

  if id.endswith('/doppler'):
    if output_format != 'csv':
      error(f"Format '{output_format}' is not supported for Doppler data")
    for filename in files:
      print_data_doppler(filename, start, stop, parameters)
    return

  if id.endswith('/drf'):
    if output_format == 'csv':
      print_data_drf_manifest(files, parameters)
      return
    if output_format == 'x_drf_zip':
      print_data_drf_zip(id, files)
      return
    error(f"Format '{output_format}' is not supported for DRF data")


def print_data_drf_manifest(observations, parameters):
  """Write one HAPI CSV record per native DRF Observation."""
  if parameters is None or parameters == []:
    parameters = ['Time', 'Observation']

  # HAPI always places Time first. If only Observation was requested, Time is
  # still returned. If only Time was requested, return only the timestamp.
  include_observation = 'Observation' in parameters
  writer = csv.writer(sys.stdout, lineterminator='\n')

  for obs_start, observation_dir in observations:
    row = [_format_hapi_time(obs_start)]
    if include_observation:
      row.append(os.path.basename(os.path.normpath(observation_dir)))
    writer.writerow(row)


def _tmp_dir():
  """Directory used to build temporary DRF ZIP archives."""
  tmp_dir = os.getenv('PSWS_TMP_DIR', tempfile.gettempdir())
  tmp_dir = os.path.abspath(os.path.expanduser(tmp_dir))
  os.makedirs(tmp_dir, exist_ok=True)
  return tmp_dir


def _safe_name(value):
  return re.sub(r'[^A-Za-z0-9_.-]+', '_', value).strip('_') or 'drf'


def _add_tree_to_zip(archive, observation_dir, station_dir):
  """Add one complete Observation tree, preserving its top-level directory."""
  for root, dirs, files in os.walk(observation_dir, followlinks=False):
    dirs.sort()
    files.sort()

    # Preserve directory entries, including empty directories.
    root_arcname = os.path.relpath(root, station_dir).replace(os.sep, '/') + '/'
    archive.write(root, arcname=root_arcname)

    for name in files:
      path = os.path.join(root, name)
      if os.path.islink(path):
        error(f"Refusing to archive symbolic link in DRF Observation: {path}")
      arcname = os.path.relpath(path, station_dir).replace(os.sep, '/')
      archive.write(path, arcname=arcname)


def _create_drf_zip(dataset_id, observations):
  """Create a temporary ZIP containing complete overlapping Observations."""
  station_id = dataset_id.rsplit('/', 1)[0]
  prefix = _safe_name(station_id) + '.drf.'

  tmp = tempfile.NamedTemporaryFile(
    prefix=prefix,
    suffix='.zip',
    dir=_tmp_dir(),
    delete=False,
  )
  zip_path = tmp.name
  tmp.close()

  try:
    # ZIP_STORED avoids spending CPU recompressing HDF5/RF payloads.
    # Zip64 is required for files/archives larger than 4 GiB.
    with zipfile.ZipFile(
      zip_path,
      mode='w',
      compression=zipfile.ZIP_STORED,
      allowZip64=True,
    ) as archive:
      for _, observation_dir in observations:
        station_dir = os.path.dirname(os.path.normpath(observation_dir))
        _add_tree_to_zip(archive, observation_dir, station_dir)

    return zip_path
  except Exception:
    try:
      os.unlink(zip_path)
    except OSError:
      pass
    raise


def print_data_drf_zip(dataset_id, observations):
  """Write DRF ZIP bytes to stdout and remove the temporary archive."""
  if not observations:
    # Match the existing provider behavior for a valid request with no data:
    # emit an empty response body.
    return

  zip_path = _create_drf_zip(dataset_id, observations)

  try:
    with open(zip_path, 'rb') as file:
      while True:
        chunk = file.read(STREAM_CHUNK_SIZE)
        if not chunk:
          break
        sys.stdout.buffer.write(chunk)
    sys.stdout.buffer.flush()
  except BrokenPipeError:
    # Client disconnected; cleanup still occurs below.
    pass
  finally:
    try:
      os.unlink(zip_path)
    except OSError as exc:
      log(f"Could not remove temporary ZIP {zip_path}: {exc}")


def print_data_doppler(filepath, start, stop, parameters):

  if parameters is None:
    parameters = ['Freq', 'Vpk']

  with open(filepath, 'r') as file:
    for line in file:
      log(f"Processing line: {line.strip()}")
      if not re.match(r'^[0-9]{4}', line):
        continue
      cols = line.split(',')
      ts = cols[0].strip()
      if ts[0:20] < start:
        continue
      if ts[0:20] >= stop:
        break

      row = ts
      if 'Freq' in parameters or 'Vpk' in parameters:
        row += ',' + cols[1].strip()
      if 'Vpk' in parameters:
        row += ',' + cols[2].strip()
      print(row)


def print_data_mag(filepath, start, stop, parameters):

  def extract_data(file):
    """Read files in a zip file into a string."""
    data = ''
    with zipfile.ZipFile(file, 'r') as archive:
      for filename in sorted(archive.namelist()):
        with archive.open(filename) as entry:
          data += entry.read().decode('utf-8')
    return data

  if parameters is None:
    parameters = ['Field_Vector', 'rxryrz', 'rt', 'lt', 'Tm']

  data = extract_data(filepath)

  for line in data.splitlines():

    log(f"Processing line: {line}")

    if line.startswith('{'):
      entry = json.loads(line)
      ts = entry['ts']
      try:
        dt = datetime.datetime.strptime(ts, '%d %b %Y %H:%M:%S')
        entry['ts'] = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
      except Exception as exc:
        error(f"Failed to parse ts '{ts}': {exc}")

    elif line.startswith('"'):
      entry = line.split(', ')
      ts = entry[0].strip('"')
      dt = datetime.datetime.strptime(ts, '%d %b %Y %H:%M:%S')
      entry = {
        'ts': dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'x': float(entry[1]),
        'y': float(entry[2]),
        'z': float(entry[3]),
        'rx': float(entry[4]),
        'ry': float(entry[5]),
        'rz': float(entry[6]),
        'rt': float(entry[7]),
        'lt': float(entry[8]),
        'Tm': float(entry[9]),
      }
    else:
      error(f"Unsupported data format in file {filepath}: {line}")

    if entry['ts'][0:20] < start:
      continue
    if entry['ts'][0:20] >= stop:
      break

    row = entry['ts']

    if 'Field_Vector' in parameters:
      row += f",{entry['x']},{entry['y']},{entry['z']}"
    if 'rxryrz' in parameters:
      row += f",{entry['rx']},{entry['ry']},{entry['rz']}"
    if 'rt' in parameters:
      row += f",{entry['rt']}"
    if 'lt' in parameters:
      row += f",{entry['lt']}"
    if 'Tm' in parameters:
      row += f",{entry['Tm']}"

    print(row)


def _data_dir():

  script_dir = os.path.dirname(os.path.abspath(__file__))
  data_dir_default = os.path.join(script_dir, '..', 'data')
  log(f"data_dir_default: {data_dir_default}")

  data_dir = os.getenv('PSWS_DATA_DIR', None)
  log(f"PSWS_DATA_DIR: {data_dir}")

  if not data_dir and not os.path.exists(data_dir_default):
    error(
      'Environment variable PSWS_DATA_DIR not set and directory '
      f'{data_dir_default} not found.'
    )

  if not data_dir and os.path.exists(data_dir_default):
    log(f"PSWS_DATA_DIR not set, using default for data_dir: {data_dir_default}")
    data_dir = data_dir_default

  try:
    data_dir = os.path.expanduser(data_dir)
  except Exception:
    error(f"Could not expand PSWS_DATA_DIR using os.path.expanduser('{data_dir}').")

  return os.path.abspath(data_dir)


def _command_line():
  if len(sys.argv) < 4:
    error(
      'At least three command line arguments needed:\n'
      '  python data.py <id> <start> <stop> [<parameters>] [<format>]'
    )

  dataset_id = sys.argv[1]
  start = sys.argv[2]
  stop = sys.argv[3]
  parameters = None
  output_format = 'csv'

  if len(sys.argv) > 4 and sys.argv[4]:
    # For convenient direct testing, permit the format as arg 4 when no
    # parameter list is needed.
    if sys.argv[4] in ['csv', 'binary', 'json', 'x_drf_zip']:
      output_format = sys.argv[4]
    else:
      parameters = [p.strip() for p in sys.argv[4].split(',') if p.strip()]

  if len(sys.argv) > 5 and sys.argv[5]:
    output_format = sys.argv[5]

  return dataset_id, start, stop, parameters, output_format


if __name__ == '__main__':
  dataset_id, start, stop, parameters, output_format = _command_line()
  data_dir = _data_dir()

  log(
    f"dataset: {dataset_id}, start: {start}, stop: {stop}, "
    f"parameters: {parameters}, format: {output_format}"
  )

  files = files_needed(dataset_id, start, stop, data_dir)
  print_data(dataset_id, files, start, stop, parameters, data_dir, output_format)
