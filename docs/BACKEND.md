# PSWS-Network Backend Documentation

This document provides detailed information about the Django backend architecture, models, views, and API.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Django Applications](#django-applications)
- [Database Models](#database-models)
- [API Endpoints](#api-endpoints)
- [Data Ingestion](#data-ingestion)
- [Background Services](#background-services)

## Architecture Overview

The PSWS-Network backend is built on Django 4.2 with a modular app structure. Each app handles a specific domain:

```
src/
├── apps/                    # Django applications
│   ├── accounts/           # User authentication and profiles
│   ├── analysis/           # Data analysis tools
│   ├── api/               # REST API endpoints
│   ├── bands/             # Ham radio band definitions
│   ├── centerfrequencies/ # Frequency catalog
│   ├── core/              # Shared utilities
│   ├── datarequests/      # Data request management
│   ├── datatypes/         # Observation type definitions
│   ├── instruments/       # Instrument management
│   ├── instrumenttypes/   # Instrument type catalog
│   ├── observations/      # Observation data management
│   └── stations/          # Station management
└── psws/                   # Project configuration
    ├── settings/          # Environment-specific settings
    │   ├── base.py       # Shared settings
    │   ├── dev.py        # Development settings
    │   └── prod.py       # Production settings
    ├── urls.py           # URL routing
    └── wsgi.py           # WSGI application
```

## Django Applications

### Accounts App

**Purpose**: User authentication, profiles, and permissions

**Key Models**:
- `Profile`: Extends Django User with additional fields
  - `email`: Contact email
  - `signup_confirmation`: Email verification status
  - `role`: User role (Admin, Science, SuperScience, User)

**Key Views**:
- `signup_view`: User registration with email verification
- `activate`: Email activation handler
- `profile`: User profile management
- `home`: Main dashboard with station map

**Features**:
- Email-based account activation
- Role-based permissions
- Station status visualization on map
- User management for admins

### Stations App

**Purpose**: Manage space weather monitoring stations

**Key Models**:
```python
class Station(models.Model):
    user = ForeignKey(User)
    station_id = CharField(max_length=10)      # Format: S000001
    station_pass = CharField(max_length=32)    # Access token
    nickname = CharField(max_length=50)
    latitude = FloatField()
    longitude = FloatField()
    grid = CharField(max_length=6)             # Maidenhead grid
    elevation = FloatField()
    antenna_1 = CharField(max_length=64)
    antenna_2 = CharField(max_length=64)
    street_address = CharField(max_length=75)
    city = CharField(max_length=75)
    state = CharField(max_length=15)
    postal_code = CharField(max_length=15)
    phone_number = CharField(max_length=20)
    create_date = DateTimeField()
    last_rID = IntegerField()                  # Last data request ID
    last_alive = DateTimeField()               # Last heartbeat
    station_status = CharField(max_length=20)  # Online/Offline/PossiblyOnline
    offlineNotify = BooleanField()             # Email notifications
```

**Station Status Logic**:
```python
# Configured in settings (hours)
ONLINE_CUT_OFF_HOURS = 24           # Default: 1 day
POSSIBLY_ONLINE_CUT_OFF_HOURS = 120 # Default: 5 days
RETIREMENT_CUT_OFF_HOURS = 504      # Default: 21 days

# Status determination
if last_alive < (now - RETIREMENT_CUT_OFF):
    status = "Retired"
elif last_alive < (now - POSSIBLY_ONLINE_CUT_OFF):
    status = "Offline"
elif last_alive < (now - ONLINE_CUT_OFF):
    status = "PossiblyOnline"
else:
    status = "Online"
```

**Key Views**:
- `add_station_view`: Create new station with automatic ID assignment
- `station_details_view`: View station details and instruments
- `update_station_view`: Edit station information
- `StationListView`: Paginated station list with filtering

**Station Creation**:
When a station is created:
1. Auto-assign next available ID (S000001, S000002, etc.)
2. Generate unique 32-character access token
3. Convert Maidenhead grid to lat/lon coordinates
4. Execute `stationcreation4.sh` to create system user and directories
5. Set up directory structure: `/home/{station_id}/`

### Instruments App

**Purpose**: Track hardware devices at each station

**Key Models**:
```python
class Instrument(models.Model):
    instrument = CharField(max_length=40)
    instrumenttype = ForeignKey(InstrumentType)
    station = ForeignKey(Station)
    serialNo = CharField(max_length=60)
    dateAdded = DateTimeField()
    dateRemoved = DateTimeField()
    status = CharField(max_length=10)
    nickname = CharField(max_length=40)
```

**Instrument Types**:
- Grape 1 Legacy (CSV format, fldigi-based)
- Grape 1 DRF (Digital RF format)
- Magnetometer (JSON/CSV magnetic field data)
- TangerineSDR (multi-channel SDR)

**Configuration File Generation**:
Instruments can download `uploader.config` with:
```ini
[profile]
token_value = {station.station_pass}
grid = {station.grid}
prefix = {station.user.username}
thestationid = {station.station_id}
central_host = pswsnetwork.caps.ua.edu

[spectrum_settings]
band = [2.5, 5.0, 10.0, 15.0, 20.0, 25.0]
instrumentid = {instrument.id}
throttle = 200K
spectrum_storage = /home/pi/PSWS/Sxfer
```

### Observations App

**Purpose**: Store and serve uploaded observation data

**Key Models**:
```python
class Observation(models.Model):
    dataType = ManyToManyField(DataType)
    dataRate = IntegerField()
    centerFrequency = ManyToManyField(CenterFrequency)
    station = ForeignKey(Station)
    instrument = ForeignKey(Instrument)
    band = ManyToManyField(Band)
    size = BigIntegerField()
    fileName = CharField(max_length=60)
    plotFile = CharField(max_length=60)
    path = CharField(max_length=60)
    plotPath = CharField(max_length=40)
    startDate = DateTimeField()
    endDate = DateTimeField()
```

**Observation Filtering**:
The `ObservationFilter` allows filtering by:
- Station (dropdown selection)
- Instrument type (multi-select)
- Center frequency (multi-select)
- Date range (start/end dates)
- Geographic bounds (lat/lon rectangle)

**Key Views**:
- `ObservationListView`: Paginated, filterable observation table
- `select_download_range`: Observation details and download options
- `download_file`: Serve observation files (with ZIP creation for DRF)
- `download_plot`: Serve generated plot images

### API App

**Purpose**: Provide REST endpoints for station heartbeats and data

**Endpoints**:

#### 1. Station List
```
GET /stations/
```
Returns all stations with status information.

#### 2. Heartbeat
```
POST /heartbeat/
```
**Request Body**:
```json
{
  "station_id": "S000028",
  "station_pass": "abc123..."
}
```

**Response** (200 OK):
```json
{
  "requestID": 5,
  "timestart": "2024-01-15T10:00:00Z",
  "timestop": "2024-01-15T11:00:00Z"
}
```

**Logic**:
1. Validate station_id and station_pass
2. Update `last_alive` timestamp
3. Check for new data requests (requestID > last_rID)
4. Return data request details if pending

#### 3. Stop Continuous Upload
```
PUT /stop/
```
**Request Body**:
```json
{
  "station_id": "S000028",
  "station_pass": "abc123..."
}
```

Sets `endDate` for the active observation.

### Analysis App

**Purpose**: Data visualization and analysis tools

**Key Features**:
- Magnetometer data plotting
- Multi-station comparison
- Interactive time-series graphs using Chart.js
- Station selection via map interface

**Key Views**:
- `analysis_map`: Interactive station map with date selector
- `display_graphs`: Multi-station magnetometer visualization

**Data Processing**:
```python
# Magnetometer data windowing
# Read 1-second samples, average every 60 seconds
# Remove DC offset (subtract mean)
# Plot X, Y, Z components on separate y-axes
```

## Database Models

### Relationships

```
User (Django) ──< Profile
                  └─< Station ──< Instrument
                                  └─< Observation ─┬─< CenterFrequency
                                                    ├─< Band
                                                    └─< DataType

InstrumentType ──< Instrument
```

### Key Constraints

1. **Station ID Uniqueness**: Enforced at application level
2. **Token Security**: 32-character random tokens
3. **Cascade Deletes**: Deleting station deletes instruments and observations
4. **Nullable Fields**: Most address/contact fields optional

## API Endpoints

### Public Download API

```
GET /observations/downloadapi/
```

**Required Parameters**:
- `start_date`: YYYY-MM-DD format
- `end_date`: YYYY-MM-DD format

**Location Filtering** (choose one):
- `station_id`: Specific station (e.g., "S000028")
- Geographic bounding box:
  - `lat_min`, `lat_max`: Latitude range (-90 to 90)
  - `lon_min`, `lon_max`: Longitude range (-180 to 180)

**Optional Filters**:
- `instrument_id`: Filter by instrument
- `frequency`: Center frequency in MHz

**Examples**:

```bash
# Download by station
curl -o output.zip \
  "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?\
station_id=S000028&start_date=2024-01-01&end_date=2024-01-31"

# Download by region (Alabama)
curl -o output.zip \
  "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?\
lat_min=32.0&lat_max=35.0&lon_min=-88.0&lon_max=-84.0&\
start_date=2024-01-01&end_date=2024-01-31"

# Filter by frequency
curl -o output.zip \
  "https://pswsnetwork.eng.ua.edu/observations/downloadapi/?\
station_id=S000028&frequency=10&start_date=2024-01-01&end_date=2024-01-31"
```

**Response Headers**:
```
X-Files-Discovered: 15
X-Files-Processed: 15
X-Files-Added: 12
X-Archive-Type: multiple-files
```

**Rate Limiting**:
- Anonymous users: 100 requests/day
- Configured via Django REST Framework throttling

**Size Limits**:
- Single file: No limit
- Multiple files: 500MB maximum total size

## Data Ingestion

### Ingestion Scripts

Located in `scripts/ingest/`:

#### 1. psws_addOBS.py
Adds Digital RF observations to database.

**Usage**:
```bash
python psws_addOBS.py \
  {dataRate} {size} {fileName} {path} \
  {station_id} {instrument_id} \
  {startDate} {endDate} \
  {freq1} {freq2} ...
```

**Process**:
1. Validate station and instrument exist
2. Extract metadata from DRF properties files
3. Create Observation record
4. Link center frequencies
5. Update station `last_alive`
6. Queue plotting task via task spooler

#### 2. psws_addMAG.py
Adds magnetometer data files.

**Usage**:
```bash
python psws_addMAG.py {path} {station_id} {instrument_id} {timestamp}
```

**Process**:
1. Scan directory for ZIP files matching `OBSYYYY-MM-DDTHH:MM.zip`
2. For each file:
   - Extract date from filename
   - Check if observation exists
   - If today's date: update size and endDate
   - If historical: create new observation with full-day endDate
3. Link magnetometer data type

#### 3. psws_addCSV.py
Adds Grape 1 Legacy CSV observations.

**Usage**:
```bash
python psws_addCSV.py {path} {station_id} {instrument_id} {trigger}
```

**Process**:
1. Parse observation timestamp from trigger filename
2. Create observation record (1-day duration)
3. Queue plot generation with `plotfldigi1.py`

## Background Services

### Watchdog Service (psws_watch10.py)

**Purpose**: Monitor station directories for upload triggers

**Mechanism**:
- Uses Python `watchdog` library with polling observer
- Watches `/home/{station_id}/` directories
- Non-recursive monitoring (one level only)
- Trigger patterns: `c*`, `m*`, `g*`, `m_Test`

**Trigger File Naming**:
```
c{timestamp}_{station_id}_#{instrument_id}  # Continuous/DRF
m{timestamp}_{station_id}_#{instrument_id}  # Magnetometer
g{timestamp}_{station_id}_#{instrument_id}  # Grape 1 Legacy
```

**Processing Flow**:
1. Watchdog detects trigger file creation
2. Parse trigger filename for metadata
3. Determine upload type (c/m/g)
4. Call appropriate ingestion script
5. Queue plotting task
6. Remove trigger file

**Service Configuration**:
```ini
[Unit]
Description=PSWS Watchdog Service
After=network.target

[Service]
Type=simple
User=psws
WorkingDirectory=/srv/PSWS-Network
ExecStart=/srv/PSWS-Network/venv312/bin/python3 \
  scripts/watchers/psws_watch10.py /home

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Plotting Services

#### Spectrum Plotter (plotspectrum_v8.py)
Generates spectrograms from Digital RF data.

**Features**:
- Reads DRF metadata and data
- Creates waterfall plots (frequency vs time)
- Plots amplitude by minute
- Supports multiple center frequencies per observation
- Calibrated amplitude (dBm) for Grape 1 DRF

#### Magnetometer Plotter (plotmag.py)
Generates 3-axis magnetic field plots.

**Features**:
- Reads JSON/CSV magnetometer logs
- 10-minute averaging
- Three y-axes for Bx, By, Bz components
- Handles ZIP and raw file formats
- Updates database with plot path

#### Grape 1 Legacy Plotter (plotfldigi1.py)
Processes CSV format observations using HamSCI geopack library.

**Features**:
- Processes fldigi CSV format
- Bandpass filtering
- Time series plots (raw and filtered)

### Audit Scripts

#### psws_audit_v4.py
Verifies database/filesystem consistency.

**Audit Types**:
```bash
python psws_audit_v4.py -a  # All audits
python psws_audit_v4.py -t  # Trigger file audit
python psws_audit_v4.py -o  # Observation file audit
python psws_audit_v4.py -d  # Data existence audit
```

**Checks**:
1. Trigger files in DB but missing from filesystem
2. Trigger files on filesystem but not in DB
3. Observation files on filesystem but not in DB
4. Observation records in DB but files missing

**Output**:
Log files in `/home/audit_logs/`:
- `trigger_in_db_{date}.log`
- `trigger_not_in_db_{date}.log`
- `obs_not_in_db_{date}.log`
- `no_obs_data_{date}.log`

## Django Management Commands

### create_profile_and_station

Creates user, profile, and station with system setup.

**Usage**:
```bash
python manage.py create_profile_and_station \
  --username johndoe \
  --email john@example.com \
  --station_id N000014 \
  --nickname "John's Station" \
  --grid FN31pr \
  --city "Los Angeles" \
  --state "CA" \
  --postal_code "90001"
```

**Process**:
1. Generate secure random password
2. Create Django User
3. Create Profile with email verification
4. Convert Maidenhead grid to coordinates
5. Create Station record
6. Execute `stationcreation4.sh` script
7. Output credentials to text file

**Output File**:
`/home/user/user_creation_outputs/{username}_details.txt`

## Environment Configuration

### Settings Structure

Three-tier settings configuration:

1. **base.py**: Shared settings loaded from environment
2. **dev.py**: Development overrides (DEBUG=True)
3. **prod.py**: Production overrides (DEBUG=False)

### Key Settings

```python
# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('PSWS_DB_NAME'),
        'USER': env('PSWS_DB_USER'),
        'PASSWORD': env('PSWS_DB_PASSWORD'),
        'HOST': env('PSWS_DB_HOST', 'localhost'),
        'PORT': env('PSWS_DB_PORT', '3306'),
    }
}

# Security
SECRET_KEY = env_required('DJANGO_SECRET_KEY')
DEBUG = env_bool('DJANGO_DEBUG', False)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS')

# Station Status Cutoffs (hours)
ONLINE_CUT_OFF_HOURS = env_int('ONLINE_CUT_OFF_HOURS', 24)
POSSIBLY_ONLINE_CUT_OFF_HOURS = env_int('POSSIBLY_ONLINE_CUT_OFF_HOURS', 120)
RETIREMENT_CUT_OFF_HOURS = env_int('RETIREMENT_CUT_OFF_HOURS', 504)
```

## Testing

Run Django tests:
```bash
python manage.py test
```

Run smoke tests:
```bash
python manage.py smoke_tests
```

## Performance Considerations

1. **Database Indexing**: Add indexes on frequently queried fields
2. **Connection Pooling**: `CONN_MAX_AGE` set to 3600 seconds
3. **Static Files**: Served by Nginx, not Django
4. **Media Files**: Consider CDN for large observation files
5. **Query Optimization**: Use `select_related()` and `prefetch_related()`

## Logging

Configure in settings:
```python
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
        },
    },
}
```

Log locations:
- Django application: `/var/log/django/django.log`
- Watchdog service: `/var/log/watchdog/watchdog.log`
- Audit logs: `/home/audit_logs/`
- API logs: `/srv/PSWS-Network/logs/observations_api.log`
