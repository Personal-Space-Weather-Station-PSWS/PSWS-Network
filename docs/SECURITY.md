# PSWS-Network Security Documentation

This document outlines security considerations, best practices, and hardening procedures for the PSWS-Network system.

## Table of Contents

- [Authentication & Authorization](#authentication--authorization)
- [Secure Deployment](#secure-deployment)
- [API Security](#api-security)
- [Database Security](#database-security)
- [File Upload Security](#file-upload-security)
- [Station Access Control](#station-access-control)
- [Security Monitoring](#security-monitoring)
- [Incident Response](#incident-response)

## Authentication & Authorization

### User Authentication

The system uses Django's built-in authentication with email verification:

**Key Features:**
- Email-based account activation
- Password hashing with PBKDF2-SHA256 (Django default)
- Session-based authentication for web interface
- Token-based authentication for station API

**Password Requirements:**
```python
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

**Security Recommendations:**
- Enforce strong passwords (minimum 12 characters recommended)
- Enable two-factor authentication (not currently implemented - future enhancement)
- Implement password expiration policies if required
- Monitor failed login attempts

### User Roles

The Profile model defines four access levels:

1. **User**: Basic access - view own stations and observations
2. **Admin**: Station operator - manage own stations, upload data
3. **Science**: Researcher - access all observation data, run analyses
4. **SuperScience**: Administrator - full system access, user management

**Access Control:**
```python
# In views
from django.contrib.auth.decorators import login_required
from apps.accounts.decorators import role_required

@login_required
@role_required(['Admin', 'SuperScience'])
def station_create(request):
    # Only Admins and SuperScience can create stations
    pass
```

### Session Security

**Session Configuration:**
```python
# settings/prod.py
SESSION_COOKIE_SECURE = True  # Only transmit over HTTPS
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_COOKIE_AGE = 1209600  # 2 weeks
```

**CSRF Protection:**
- All POST requests require CSRF tokens
- CSRF tokens embedded in forms via `{% csrf_token %}`
- API endpoints use token authentication instead of session cookies

## Secure Deployment

### HTTPS Configuration

**Mandatory for production:**

```nginx
# /etc/nginx/sites-available/psws
server {
    listen 443 ssl http2;
    server_name pswsnetwork.eng.ua.edu;
    
    ssl_certificate /etc/letsencrypt/live/pswsnetwork.eng.ua.edu/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/pswsnetwork.eng.ua.edu/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # HSTS
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name pswsnetwork.eng.ua.edu;
    return 301 https://$server_name$request_uri;
}
```

**Let's Encrypt SSL Setup:**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d pswsnetwork.eng.ua.edu
sudo systemctl enable certbot.timer
```

### Django Security Settings

**Required for Production:**

```python
# settings/prod.py

# Disable debug mode
DEBUG = False

# Restrict allowed hosts
ALLOWED_HOSTS = ['pswsnetwork.eng.ua.edu']

# Secure cookies
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content security
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# CSRF protection
CSRF_COOKIE_HTTPONLY = True
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SAMESITE = 'Strict'
```

### Secret Key Management

**Never commit secrets to version control:**

```bash
# Generate secure secret key
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Store in environment file (not in git)
echo "DJANGO_SECRET_KEY='generated-key-here'" >> /srv/PSWS-Network/deploy/env/psws.env
chmod 600 /srv/PSWS-Network/deploy/env/psws.env
```

**Environment file protection:**
```bash
# Add to .gitignore
echo "deploy/env/psws.env" >> .gitignore
echo "*.pyc" >> .gitignore
echo "__pycache__/" >> .gitignore
```

### File System Permissions

```bash
# Application directory
sudo chown -R psws:psws /srv/PSWS-Network
chmod 755 /srv/PSWS-Network

# Writable directories
sudo mkdir -p /var/log/django /var/log/watchdog
sudo chown psws:psws /var/log/django /var/log/watchdog
chmod 755 /var/log/django /var/log/watchdog

# Station data directory
sudo mkdir -p /home/stations
sudo chown psws:psws /home/stations
chmod 750 /home/stations

# Media files
chmod 755 /srv/PSWS-Network/media
chmod 755 /srv/PSWS-Network/media/plots

# Sensitive files
chmod 600 /srv/PSWS-Network/deploy/env/psws.env
```

## API Security

### Station Access Tokens

Each station has a unique 32-character access token for API authentication.

**Token Generation:**
```python
# In Station model
import secrets

def generate_access_token():
    return secrets.token_urlsafe(24)[:32]
```

**Token Usage:**
```bash
# Heartbeat API
curl -X POST https://pswsnetwork.eng.ua.edu/api/heartbeat/ \
  -H "Content-Type: application/json" \
  -d '{
    "station_id": "S000001",
    "access_token": "abcd1234efgh5678ijkl9012mnop3456"
  }'
```

**Token Security:**
- Tokens stored hashed in database (future enhancement)
- Transmitted only over HTTPS
- Included in uploader.config files with restricted permissions
- Regenerate if compromised

### Rate Limiting

**Public Download API:**
```python
# observations/views.py
from django.core.cache import cache

def check_rate_limit(request):
    key = f"api_download_{request.META.get('REMOTE_ADDR')}"
    count = cache.get(key, 0)
    
    if count >= 100:  # 100 requests per day
        raise PermissionDenied("Rate limit exceeded")
    
    cache.set(key, count + 1, 86400)  # 24-hour window
```

**Recommendations:**
- Implement IP-based rate limiting (100 downloads/day for anonymous)
- Authenticated users get higher limits
- Use django-ratelimit or similar middleware
- Monitor API usage in logs

### Input Validation

**SQL Injection Prevention:**
- Always use Django ORM (parameterized queries)
- Never use raw SQL with user input
- Use `.filter()` with Q objects for complex queries

**Example - Secure Filtering:**
```python
# GOOD - Parameterized query
observations = Observation.objects.filter(
    station__stationID=station_id,
    startDate__gte=start_date
)

# BAD - Never do this
observations = Observation.objects.raw(
    f"SELECT * FROM observations WHERE station_id = '{station_id}'"
)
```

**XSS Prevention:**
- Django templates auto-escape by default
- Use `|safe` filter only for trusted content
- Sanitize user input with bleach library if needed

```python
import bleach

def clean_user_input(text):
    allowed_tags = ['p', 'br', 'strong', 'em']
    return bleach.clean(text, tags=allowed_tags, strip=True)
```

## Database Security

### MariaDB Hardening

**Secure Installation:**
```bash
sudo mysql_secure_installation
# - Set root password
# - Remove anonymous users
# - Disallow root login remotely
# - Remove test database
# - Reload privilege tables
```

**User Privileges:**
```sql
-- Create dedicated user with minimal privileges
CREATE USER 'psws_user'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON psws_db.* TO 'psws_user'@'localhost';
FLUSH PRIVILEGES;

-- Never use root for application
-- Never grant ALL PRIVILEGES unless necessary
```

**Connection Security:**
```python
# settings/prod.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
            'use_unicode': True,
            'ssl': {
                'ca': '/path/to/ca-cert.pem',
                # Enable SSL for remote connections
            }
        }
    }
}
```

**Backup Strategy:**
```bash
#!/bin/bash
# /usr/local/bin/backup_psws_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/var/backups/psws
mkdir -p $BACKUP_DIR

mysqldump -u psws_user -p psws_db | gzip > $BACKUP_DIR/psws_db_$DATE.sql.gz

# Keep 30 days of backups
find $BACKUP_DIR -name "psws_db_*.sql.gz" -mtime +30 -delete

# Set restrictive permissions
chmod 600 $BACKUP_DIR/psws_db_$DATE.sql.gz
```

**Cron Job:**
```bash
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup_psws_db.sh
```

## File Upload Security

### Upload Validation

**Station Uploader Configuration:**
```python
# scripts/ingest/psws_addOBS.py
import os

def validate_upload_path(station_id, filename):
    # Prevent path traversal
    safe_filename = os.path.basename(filename)
    allowed_path = f"/home/{station_id}"
    
    # Construct safe path
    upload_path = os.path.join(allowed_path, safe_filename)
    
    # Verify it's within allowed directory
    real_path = os.path.realpath(upload_path)
    if not real_path.startswith(allowed_path):
        raise ValueError("Invalid upload path")
    
    return upload_path
```

**File Type Validation:**
```python
ALLOWED_EXTENSIONS = {
    'drf': ['.h5', '.hdf5'],
    'csv': ['.csv'],
    'magnetometer': ['.zip', '.json'],
}

def validate_file_type(filename, expected_type):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS[expected_type]:
        raise ValueError(f"Invalid file extension: {ext}")
```

**Size Limits:**
```python
# settings/prod.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 524288000  # 500 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000

# Nginx configuration
client_max_body_size 500M;
```

### Directory Isolation

Each station gets isolated directory:
```bash
# Station directory structure
/home/
├── S000001/
│   ├── uploader.config
│   ├── data/
│   └── logs/
├── S000002/
│   ├── uploader.config
│   ├── data/
│   └── logs/
```

**Permissions:**
```bash
# Restrict station directories
chmod 750 /home/S000001
chown psws:psws /home/S000001

# uploader.config contains sensitive tokens
chmod 600 /home/S000001/uploader.config
```

## Station Access Control

### Access Token Management

**Token Storage:**
```python
# Station model
class Station(models.Model):
    access_token = models.CharField(max_length=32, unique=True)
    
    def save(self, *args, **kwargs):
        if not self.access_token:
            self.access_token = self.generate_access_token()
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_access_token():
        return secrets.token_urlsafe(24)[:32]
```

**Token Validation:**
```python
# api/views.py
def validate_station_credentials(station_id, access_token):
    try:
        station = Station.objects.get(
            stationID=station_id,
            access_token=access_token
        )
        return station
    except Station.DoesNotExist:
        raise PermissionDenied("Invalid credentials")
```

**Token Rotation:**
```python
# Management command
def rotate_station_token(station_id):
    station = Station.objects.get(stationID=station_id)
    old_token = station.access_token
    station.access_token = Station.generate_access_token()
    station.save()
    
    # Log token rotation
    logger.warning(f"Token rotated for station {station_id}")
    
    # Notify station operator
    send_mail(
        subject="Station Access Token Rotated",
        message=f"New token: {station.access_token}",
        from_email="noreply@pswsnetwork.eng.ua.edu",
        recipient_list=[station.profile.user.email]
    )
```

### Heartbeat Security

The heartbeat endpoint validates station identity:

```python
# api/views.py
@csrf_exempt
@require_http_methods(["POST"])
def heartbeat(request):
    data = json.loads(request.body)
    station_id = data.get('station_id')
    access_token = data.get('access_token')
    
    # Validate credentials
    station = validate_station_credentials(station_id, access_token)
    
    # Update last alive timestamp
    station.last_alive = timezone.now()
    station.save()
    
    # Return any pending data requests
    return JsonResponse({"status": "ok"})
```

## Security Monitoring

### Logging

**Django Application Logs:**
```python
# settings/prod.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/django.log',
        },
        'security': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/var/log/django/security.log',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['security'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
```

**Failed Login Monitoring:**
```python
# accounts/views.py
from django.contrib.auth.signals import user_login_failed
from django.dispatch import receiver

@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    logger.warning(
        f"Failed login attempt for {credentials.get('username')} "
        f"from {request.META.get('REMOTE_ADDR')}"
    )
```

**Log Rotation:**
```bash
# /etc/logrotate.d/psws
/var/log/django/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 psws psws
    sharedscripts
    postrotate
        systemctl reload psws-gunicorn
    endscript
}
```

### Security Auditing

**Regular Security Checks:**
```bash
# Check for suspicious files
find /home/stations -type f -name "*.php" -o -name "*.exe"

# Monitor failed authentication
grep "Failed login" /var/log/django/security.log

# Check file permissions
find /srv/PSWS-Network -type f -perm /o+w

# Review database users
mysql -u root -p -e "SELECT User, Host FROM mysql.user;"
```

**Automated Security Scanning:**
```bash
# Install security scanner
pip install safety bandit

# Check Python dependencies
safety check

# Static code analysis
bandit -r /srv/PSWS-Network/src/
```

## Incident Response

### Compromised Station Token

1. **Immediately rotate token:**
   ```bash
   python manage.py shell
   >>> from apps.stations.models import Station
   >>> station = Station.objects.get(stationID='S000001')
   >>> station.access_token = Station.generate_access_token()
   >>> station.save()
   ```

2. **Review access logs:**
   ```bash
   grep "S000001" /var/log/django/django.log | grep heartbeat
   ```

3. **Notify station operator**

4. **Audit uploaded data for anomalies**

### Suspected Data Breach

1. **Isolate affected systems**
2. **Preserve logs and evidence**
3. **Review database access logs**
4. **Reset all user passwords**
5. **Rotate all station access tokens**
6. **Notify affected users if PII exposed**
7. **Report to NSF if grant-related**

### Database Compromise

1. **Disconnect database from network**
2. **Restore from clean backup**
3. **Review database audit logs**
4. **Change all database passwords**
5. **Update application credentials**
6. **Scan for SQL injection vulnerabilities**

## Security Checklist

### Pre-Deployment

- [ ] DEBUG = False in production settings
- [ ] Strong SECRET_KEY generated and secured
- [ ] ALLOWED_HOSTS configured
- [ ] SSL certificate installed and configured
- [ ] HTTPS redirects enabled
- [ ] Security headers configured in Nginx
- [ ] Database user has minimal privileges
- [ ] All passwords are strong and unique
- [ ] Environment files not in version control
- [ ] File permissions properly restricted
- [ ] Firewall configured (UFW or iptables)
- [ ] SSH key authentication enabled
- [ ] Root login disabled

### Post-Deployment

- [ ] Log rotation configured
- [ ] Automated backups running
- [ ] Security monitoring in place
- [ ] Rate limiting enabled on APIs
- [ ] Failed login monitoring active
- [ ] Security updates applied
- [ ] Vulnerability scanning configured
- [ ] Incident response plan documented
- [ ] Staff trained on security procedures

### Ongoing Maintenance

- [ ] Review logs weekly
- [ ] Apply security patches monthly
- [ ] Rotate secrets quarterly
- [ ] Audit user accounts quarterly
- [ ] Review API access annually
- [ ] Security penetration test annually
- [ ] Disaster recovery drill annually

## Additional Resources

- [Django Security Documentation](https://docs.djangoproject.com/en/stable/topics/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CIS Benchmarks for Linux](https://www.cisecurity.org/cis-benchmarks/)
- [Let's Encrypt SSL](https://letsencrypt.org/)
- [Mozilla SSL Configuration Generator](https://ssl-config.mozilla.org/)

## Reporting Security Issues

If you discover a security vulnerability:

1. **Do not** open a public GitHub issue
2. Email: bill.engelke@cs.ua.edu with subject "SECURITY"
3. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours.
