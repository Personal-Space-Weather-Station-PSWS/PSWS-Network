# PSWS-Network Administrator Guide

This guide covers administrative tasks, system management, and operational procedures for the PSWS-Network.

## Table of Contents

- [User Management](#user-management)
- [Station Management](#station-management)
- [Data Management](#data-management)
- [System Monitoring](#system-monitoring)
- [Maintenance Tasks](#maintenance-tasks)
- [Troubleshooting](#troubleshooting)
- [Backup and Recovery](#backup-and-recovery)

## User Management

### Django Admin Interface

Access the admin interface at: `https://your-domain/admin/`

**Key Admin Models:**
- Users (django.contrib.auth)
- Profiles (apps.accounts)
- Stations (apps.stations)
- Instruments (apps.instruments)
- Observations (apps.observations)

### Creating User Accounts

#### Via Admin Interface

1. Navigate to `/admin/auth/user/`
2. Click "Add User"
3. Enter username and password
4. Save and continue editing
5. Fill in email and personal information
6. Set permissions (staff status, superuser, etc.)
7. Save

A Profile will be automatically created via signals.

#### Via Management Command

```bash
python manage.py createsuperuser --username=admin --email=admin@example.com
```

#### Via Custom Management Command (With Station)

```bash
# Create user, profile, and station in one command
python manage.py create_profile_and_station \
    --username johndoe \
    --email john@example.com \
    --password SecurePass123 \
    --role Admin \
    --nickname "John's Station" \
    --grid EM50aa \
    --elevation 200
```

This command:
- Creates user account
- Creates profile with specified role
- Creates station linked to profile
- Executes `stationcreation4.sh` script
- Outputs credentials to `/home/johndoe/user_creation_outputs/`

### User Roles and Permissions

**Profile Roles:**

1. **User**: 
   - View own stations
   - View public observations
   - Basic dashboard access

2. **Admin**:
   - Create and manage own stations
   - Upload observation data
   - Manage own instruments
   - All User permissions

3. **Science**:
   - Access all observation data
   - Run analysis tools
   - Download bulk data
   - All User permissions

4. **SuperScience**:
   - Full system access
   - User management
   - Station approval/rejection
   - System configuration
   - All permissions

**Setting User Role:**

```bash
python manage.py shell
>>> from apps.accounts.models import Profile
>>> profile = Profile.objects.get(user__username='johndoe')
>>> profile.role = 'Science'
>>> profile.save()
```

### Email Verification

**Manual Verification:**

If email verification fails or needs manual approval:

```bash
python manage.py shell
>>> from apps.accounts.models import Profile
>>> profile = Profile.objects.get(user__username='johndoe')
>>> profile.email_verified = True
>>> profile.save()
```

**Resend Verification Email:**

```python
from django.core.mail import send_mail
from django.contrib.sites.models import Site

def resend_verification(user):
    profile = user.profile
    token = profile.generate_verification_token()
    site = Site.objects.get_current()
    
    verification_url = f"https://{site.domain}/accounts/verify/{token}/"
    
    send_mail(
        subject="Verify your PSWS account",
        message=f"Please verify your account: {verification_url}",
        from_email="noreply@pswsnetwork.eng.ua.edu",
        recipient_list=[user.email]
    )
```

### Disabling User Accounts

**Soft Disable (Account Deactivation):**

```bash
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='johndoe')
>>> user.is_active = False
>>> user.save()
```

**Hard Delete (Remove All Data):**

```bash
# WARNING: This deletes user, profile, stations, and observations
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='johndoe')
>>> user.delete()
```

## Station Management

### Station Lifecycle

**Station States:**
- **Online**: Last heartbeat < 24 hours
- **PossiblyOnline**: Last heartbeat < 120 hours (5 days)
- **Offline**: Last heartbeat < 504 hours (21 days)
- **Retired**: Last heartbeat > 504 hours

**Configurable Cutoff Hours:**

```python
# settings/base.py
STATION_STATUS_CUTOFF_HOURS = {
    'online': 24,           # 1 day
    'possibly_online': 120, # 5 days
    'offline': 504,         # 21 days
}
```

### Creating Stations

#### Via Web Interface

Users with Admin role can create stations at `/stations/add/`

Required fields:
- Nickname
- Maidenhead grid locator (validated)
- Elevation (meters)

Optional fields:
- Antennas (description)
- Street address
- Phone number

#### Via Management Command

```bash
python manage.py shell
>>> from apps.stations.models import Station
>>> from apps.accounts.models import Profile
>>> 
>>> profile = Profile.objects.get(user__username='johndoe')
>>> station = Station.objects.create(
...     profile=profile,
...     nickname="Test Station",
...     grid="EM50aa",
...     elevation=200,
...     antennas="Dipole, Vertical"
... )
>>> station.stationID
'S000042'
>>> station.access_token
'abcd1234efgh5678ijkl9012mnop3456'
```

#### Station Creation Script

The `stationcreation4.sh` script is automatically executed when stations are created via the management command:

```bash
# Manually execute for existing station
/srv/PSWS-Network/scripts/stationcreation4.sh S000042 johndoe
```

This creates:
- Station directory: `/home/S000042/`
- Uploader configuration: `/home/S000042/uploader.config`
- Log directories
- Sets proper permissions

### Viewing Station Details

**Via Admin Interface:**

Navigate to `/admin/stations/station/` and select station.

**Via Shell:**

```bash
python manage.py shell
>>> from apps.stations.models import Station
>>> station = Station.objects.get(stationID='S000001')
>>> print(f"ID: {station.stationID}")
>>> print(f"Status: {station.status()}")
>>> print(f"Latitude: {station.latitude}")
>>> print(f"Longitude: {station.longitude}")
>>> print(f"Last Heartbeat: {station.last_alive}")
>>> print(f"Token: {station.access_token}")
```

### Station Access Token Management

**Viewing Token:**

```bash
python manage.py shell
>>> from apps.stations.models import Station
>>> station = Station.objects.get(stationID='S000001')
>>> print(station.access_token)
```

**Rotating Token:**

```bash
python manage.py shell
>>> from apps.stations.models import Station
>>> import secrets
>>> 
>>> station = Station.objects.get(stationID='S000001')
>>> old_token = station.access_token
>>> station.access_token = secrets.token_urlsafe(24)[:32]
>>> station.save()
>>> 
>>> print(f"Old token: {old_token}")
>>> print(f"New token: {station.access_token}")
```

After rotating, update `/home/S000001/uploader.config` with new token.

### Retiring Stations

**Mark as Retired:**

```bash
python manage.py shell
>>> from apps.stations.models import Station
>>> station = Station.objects.get(stationID='S000001')
>>> station.retired = True
>>> station.save()
```

Retired stations:
- No longer accept heartbeats
- Not displayed on map as active
- Historical data remains accessible

## Data Management

### Instrument Types

**View Existing Types:**

```bash
python manage.py shell
>>> from apps.instrumenttypes.models import InstrumentType
>>> for it in InstrumentType.objects.all():
...     print(it.instrumentType)
```

**Add New Instrument Type:**

```bash
python manage.py shell
>>> from apps.instrumenttypes.models import InstrumentType
>>> InstrumentType.objects.create(instrumentType='New SDR Model')
```

### Center Frequencies

**View Frequencies:**

```bash
python manage.py shell
>>> from apps.centerfrequencies.models import CenterFrequency
>>> for cf in CenterFrequency.objects.all().order_by('centerFrequency'):
...     print(f"{cf.centerFrequency} MHz")
```

**Add New Frequency:**

```bash
python manage.py shell
>>> from apps.centerfrequencies.models import CenterFrequency
>>> CenterFrequency.objects.create(centerFrequency=30.0)
```

### Managing Observations

**Search Observations:**

```bash
python manage.py shell
>>> from apps.observations.models import Observation
>>> from datetime import datetime
>>> 
>>> # Today's observations
>>> today = datetime.now().date()
>>> obs = Observation.objects.filter(startDate__date=today)
>>> print(f"Observations today: {obs.count()}")
>>> 
>>> # By station
>>> station_obs = Observation.objects.filter(station__stationID='S000001')
>>> print(f"Station S000001 observations: {station_obs.count()}")
>>> 
>>> # By frequency
>>> freq_obs = Observation.objects.filter(centerFrequency__centerFrequency=5.0)
>>> print(f"5 MHz observations: {freq_obs.count()}")
```

**Delete Observations:**

```bash
# Delete specific observation
python manage.py shell
>>> from apps.observations.models import Observation
>>> obs = Observation.objects.get(pk=12345)
>>> obs.delete()

# Bulk delete (CAUTION)
>>> from datetime import datetime, timedelta
>>> cutoff = datetime.now() - timedelta(days=365)
>>> old_obs = Observation.objects.filter(startDate__lt=cutoff)
>>> print(f"Will delete {old_obs.count()} observations")
>>> # old_obs.delete()  # Uncomment to execute
```

**Data Integrity Check:**

```bash
# Run audit script
cd /srv/PSWS-Network/scripts/audit
python psws_audit_v4.py

# Review output
cat /home/audit_logs/audit_YYYYMMDD_HHMMSS.log
```

The audit script checks:
- Orphaned trigger files
- Missing observation files
- Database/filesystem mismatches
- Invalid data references

## System Monitoring

### Service Status

**Check Django Application:**

```bash
# Gunicorn service
sudo systemctl status psws-gunicorn
sudo journalctl -u psws-gunicorn -f

# Nginx
sudo systemctl status nginx
sudo nginx -t

# MariaDB
sudo systemctl status mariadb
```

**Check Watchdog Service:**

```bash
# Check if running
ps aux | grep psws_watch10

# Start manually
cd /srv/PSWS-Network/scripts/watchers
python psws_watch10.py &

# View logs
tail -f /var/log/watchdog/watchdog.log
```

### Log Monitoring

**Django Application Logs:**

```bash
# Main application log
tail -f /var/log/django/django.log

# Security events
tail -f /var/log/django/security.log

# Nginx access log
sudo tail -f /var/log/nginx/access.log

# Nginx error log
sudo tail -f /var/log/nginx/error.log
```

**Search for Errors:**

```bash
# Recent errors
grep -i error /var/log/django/django.log | tail -20

# Failed logins
grep "Failed login" /var/log/django/security.log

# Database errors
grep -i "database" /var/log/django/django.log | tail -20
```

### Database Monitoring

**Connection Status:**

```bash
# Active connections
mysql -u root -p -e "SHOW PROCESSLIST;"

# Database size
mysql -u root -p -e "
SELECT 
    table_schema AS 'Database',
    ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)'
FROM information_schema.tables 
WHERE table_schema = 'psws_db'
GROUP BY table_schema;
"

# Table row counts
mysql -u psws_user -p psws_db -e "
SELECT 
    table_name,
    table_rows 
FROM information_schema.tables 
WHERE table_schema = 'psws_db' 
ORDER BY table_rows DESC;
"
```

**Query Performance:**

```bash
# Enable slow query log
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf

# Add:
# slow_query_log = 1
# slow_query_log_file = /var/log/mysql/slow-queries.log
# long_query_time = 2

sudo systemctl restart mariadb

# Review slow queries
sudo tail -f /var/log/mysql/slow-queries.log
```

### Disk Usage

**Check Disk Space:**

```bash
# Overall disk usage
df -h

# Station data directories
du -sh /home/S*

# Observation plots
du -sh /srv/PSWS-Network/media/plots

# Database size
sudo du -sh /var/lib/mysql/psws_db/
```

**Clean Up Old Data:**

```bash
# Old plot files (older than 90 days)
find /srv/PSWS-Network/media/plots -name "*.png" -mtime +90 -delete

# Old logs (handled by logrotate)
# See /etc/logrotate.d/psws

# Temporary files
rm -rf /psws/temp/ziptemp/*
```

## Maintenance Tasks

### Database Maintenance

**Optimize Tables:**

```bash
mysql -u root -p psws_db -e "OPTIMIZE TABLE observations;"
mysql -u root -p psws_db -e "OPTIMIZE TABLE stations;"
```

**Update Statistics:**

```bash
mysql -u root -p psws_db -e "ANALYZE TABLE observations;"
```

**Check for Corruption:**

```bash
mysql -u root -p psws_db -e "CHECK TABLE observations;"
```

### Django Maintenance

**Clear Sessions:**

```bash
# Remove expired sessions
python manage.py clearsessions
```

**Update Static Files:**

```bash
# After code updates
python manage.py collectstatic --clear --noinput
```

**Database Migrations:**

```bash
# Check for pending migrations
python manage.py showmigrations

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

### System Updates

**Update Python Packages:**

```bash
source /srv/PSWS-Network/venv312/bin/activate
pip list --outdated
pip install --upgrade package_name

# Update requirements.txt
pip freeze > requirements.txt
```

**Update Operating System:**

```bash
sudo apt update
sudo apt upgrade
sudo apt autoremove
sudo reboot  # If kernel updated
```

## Troubleshooting

### Common Issues

#### Station Not Receiving Heartbeats

**Check:**
1. Station configuration:
   ```bash
   cat /home/S000001/uploader.config
   ```
2. Network connectivity from station
3. API endpoint accessibility:
   ```bash
   curl -X POST https://pswsnetwork.eng.ua.edu/api/heartbeat/ \
     -H "Content-Type: application/json" \
     -d '{"station_id": "S000001", "access_token": "token"}'
   ```
4. Nginx logs for rejected requests

#### Data Not Ingesting

**Check Watchdog:**
```bash
# Is watchdog running?
ps aux | grep psws_watch10

# Any errors in log?
tail -100 /var/log/watchdog/watchdog.log

# Check trigger files
ls -la /home/S000001/c*
ls -la /home/S000001/m*
```

**Manual Ingestion:**
```bash
cd /srv/PSWS-Network/scripts/ingest
source ../../venv312/bin/activate

# For DRF data
python psws_addOBS.py S000001 /path/to/data.h5 2.5

# For magnetometer
python psws_addMAG.py S000001 /path/to/mag.zip

# For CSV (Grape 1)
python psws_addCSV.py S000001 /path/to/data.csv
```

#### Plots Not Generating

**Check Plot Queue:**
```bash
# Check for queued plots
python manage.py shell
>>> from apps.observations.models import Observation
>>> queued = Observation.objects.filter(plot_queued=True)
>>> print(f"Queued: {queued.count()}")
```

**Manual Plot Generation:**
```bash
cd /srv/PSWS-Network/scripts/plotters
source ../../venv312/bin/activate

# For spectrum data
python plotspectrum_v8.py /path/to/data.h5 S000001

# For magnetometer
python plotmag.py /path/to/mag.zip S000001
```

#### 502 Bad Gateway

**Check Gunicorn:**
```bash
sudo systemctl status psws-gunicorn
sudo journalctl -u psws-gunicorn -n 50

# Restart if needed
sudo systemctl restart psws-gunicorn
```

**Check Socket:**
```bash
ls -la /srv/PSWS-Network/gunicorn.sock
sudo chown psws:www-data /srv/PSWS-Network/gunicorn.sock
```

#### Database Connection Errors

**Check MariaDB:**
```bash
sudo systemctl status mariadb

# Test connection
mysql -u psws_user -p psws_db -e "SELECT 1;"
```

**Check Credentials:**
```bash
cat /srv/PSWS-Network/deploy/env/psws.env | grep DB
```

**Check Connection Limits:**
```bash
mysql -u root -p -e "SHOW VARIABLES LIKE 'max_connections';"
mysql -u root -p -e "SHOW STATUS LIKE 'Threads_connected';"
```

## Backup and Recovery

### Automated Backups

**Database Backup Script:**

```bash
#!/bin/bash
# /usr/local/bin/backup_psws.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/psws
mkdir -p $BACKUP_DIR

# Database backup
mysqldump -u psws_user -p'password' psws_db | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Media files backup
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /srv/PSWS-Network/media/

# Station configurations
tar -czf $BACKUP_DIR/stations_$DATE.tar.gz /home/S*/uploader.config

# Keep 30 days of backups
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

**Schedule with Cron:**

```bash
sudo crontab -e

# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup_psws.sh >> /var/log/backups/psws_backup.log 2>&1
```

### Database Recovery

**Restore from Backup:**

```bash
# Stop application
sudo systemctl stop psws-gunicorn

# Restore database
gunzip < /var/backups/psws/db_20260216_020000.sql.gz | \
mysql -u psws_user -p psws_db

# Restart application
sudo systemctl start psws-gunicorn
```

### Disaster Recovery

**Full System Restore:**

1. Install fresh Rocky 10
2. Install dependencies (MariaDB, Python, etc.)
3. Clone repository
4. Restore database backup
5. Restore media files backup
6. Restore station configurations
7. Configure environment
8. Start services

**Recovery Time Objective (RTO):** ~4 hours  
**Recovery Point Objective (RPO):** Daily backups (24 hours)

## Administrative Scripts

### Useful Management Commands

```bash
# Create superuser
python manage.py createsuperuser

# Shell access
python manage.py shell

# Database shell
python manage.py dbshell

# Show migrations
python manage.py showmigrations

# Check deployment
python manage.py check --deploy

# Clear cache
python manage.py clear_cache  # If implemented

# Create station
python manage.py create_profile_and_station \
    --username test --email test@example.com \
    --password test123 --role Admin \
    --nickname "Test" --grid EM50aa --elevation 100
```

### Bulk Operations

**Export Observations to CSV:**

```python
# export_observations.py
from apps.observations.models import Observation
import csv

with open('observations_export.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['ID', 'Station', 'Start Date', 'End Date', 'Frequency'])
    
    for obs in Observation.objects.all():
        writer.writerow([
            obs.observationID,
            obs.station.stationID,
            obs.startDate,
            obs.endDate,
            obs.centerFrequency.centerFrequency if obs.centerFrequency else 'N/A'
        ])
```

**Bulk Station Updates:**

```python
# Update all stations in a grid square
from apps.stations.models import Station

for station in Station.objects.filter(grid__startswith='EM'):
    # Example: Update antenna information
    station.antennas = "Updated: " + (station.antennas or "")
    station.save()
```

## Performance Tuning

### Database Optimization

**Add Indexes:**

```python
# In models.py
class Observation(models.Model):
    startDate = models.DateTimeField(db_index=True)
    station = models.ForeignKey(Station, db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['startDate', 'station']),
            models.Index(fields=['centerFrequency', 'startDate']),
        ]
```

**Query Optimization:**

```python
# Use select_related for foreign keys
observations = Observation.objects.select_related(
    'station', 'instrument', 'centerFrequency'
).filter(startDate__gte=start_date)

# Use prefetch_related for many-to-many
observations = Observation.objects.prefetch_related(
    'dataType', 'band'
).all()
```

### Application Tuning

**Gunicorn Workers:**

```ini
# /etc/systemd/system/psws-gunicorn.service
ExecStart=/srv/PSWS-Network/venv312/bin/gunicorn \
    --workers 4 \
    --worker-class gthread \
    --threads 2 \
    --bind unix:/srv/PSWS-Network/gunicorn.sock \
    psws.wsgi:application
```

Workers = (2 × CPU cores) + 1

**Nginx Caching:**

```nginx
# Cache static files
location /static/ {
    expires 30d;
    add_header Cache-Control "public, immutable";
}

# Cache plots
location /media/plots/ {
    expires 7d;
    add_header Cache-Control "public";
}
```

## Contact and Support

For administrative assistance:
- Email: bill.engelke@cs.ua.edu
- Documentation: https://github.com/Personal-Space-Weather-Station-PSWS/PSWS-Network/wiki
