# PSWS-Network Deployment Guide

This guide covers production deployment of the PSWS-Network system on Ubuntu 24 LTS.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [System Preparation](#system-preparation)
- [Application Deployment](#application-deployment)
- [Gunicorn Configuration](#gunicorn-configuration)
- [Nginx Configuration](#nginx-configuration)
- [SSL Setup](#ssl-setup)
- [Watchdog Service](#watchdog-service)
- [Post-Deployment](#post-deployment)
- [Monitoring](#monitoring)
- [Updates](#updates)

## Overview

The production deployment uses:
- **Gunicorn** as the WSGI application server
- **Nginx** as the reverse proxy and static file server
- **Systemd** for service management
- **Let's Encrypt** for SSL certificates
- **MariaDB** as the database backend

## Prerequisites

### System Requirements

- **OS**: Rocky 10
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 500GB+ (depends on observation data volume)
- **Network**: Static IP address, domain name configured

### Domain Configuration

Before deployment, ensure DNS is configured:

```bash
# Check DNS resolution
dig pswsnetwork.eng.ua.edu

# Should return your server's IP address
```

### Firewall Preparation

```bash
# Install UFW
sudo apt install ufw

# Allow SSH (IMPORTANT: Do this first!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
sudo ufw status
```

## System Preparation

### Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential python3.12 python3.12-venv \
    python3-pip python3-dev git nginx mariadb-server \
    libmariadb-dev libssl-dev libffi-dev certbot \
    python3-certbot-nginx
```

### Create Application User

```bash
# Create dedicated user for application
sudo useradd -m -s /bin/bash psws
sudo usermod -aG sudo psws  # Optional: for deployment tasks

# Set up SSH key for deployment (optional)
sudo mkdir /home/psws/.ssh
sudo cp ~/.ssh/authorized_keys /home/psws/.ssh/
sudo chown -R psws:psws /home/psws/.ssh
sudo chmod 700 /home/psws/.ssh
sudo chmod 600 /home/psws/.ssh/authorized_keys
```

### Configure MariaDB

```bash
# Secure installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p
```

```sql
CREATE DATABASE psws_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'psws_user'@'localhost' IDENTIFIED BY 'STRONG_PASSWORD_HERE';
GRANT ALL PRIVILEGES ON psws_db.* TO 'psws_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

**Tune MariaDB for Performance:**

```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

Add/modify:
```ini
[mysqld]
innodb_buffer_pool_size = 4G  # 50-70% of RAM
innodb_log_file_size = 256M
max_connections = 200
query_cache_size = 0  # Disabled in MariaDB 10.5+
query_cache_type = 0
```

```bash
sudo systemctl restart mariadb
```

## Application Deployment

### Clone Repository

```bash
# Switch to psws user
sudo su - psws

# Create application directory
cd /srv
sudo mkdir -p /srv/PSWS-Network
sudo chown psws:psws /srv/PSWS-Network
cd /srv/PSWS-Network

# Clone repository
git clone https://github.com/yourusername/PSWS-Network.git .

# Or for private repo
git clone git@github.com:yourusername/PSWS-Network.git .
```

### Python Virtual Environment

```bash
# Create virtual environment
python3.12 -m venv venv312
source venv312/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install Gunicorn
pip install gunicorn
```

### Environment Configuration

```bash
# Copy environment template
cp deploy/env/psws.env.example deploy/env/psws.env

# Edit configuration
nano deploy/env/psws.env
```

**Critical Settings:**

```bash
# Django Core
DJANGO_SECRET_KEY="$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')"
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=pswsnetwork.eng.ua.edu
DJANGO_SETTINGS_MODULE=psws.settings.prod

# Database
PSWS_DB_NAME=psws_db
PSWS_DB_USER=psws_user
PSWS_DB_PASSWORD=STRONG_PASSWORD_HERE
PSWS_DB_HOST=localhost
PSWS_DB_PORT=3306

# External Services
MAPBOX_ACCESS_TOKEN=pk.your_mapbox_token_here

# Paths
ACCOUNT_ACTIVATION_LOG_PATH=/var/log/django/
STATIC_ROOT=/srv/PSWS-Network/static/
MEDIA_ROOT=/srv/PSWS-Network/media/

# Email (configure for production)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

**Secure Environment File:**

```bash
chmod 600 /srv/PSWS-Network/deploy/env/psws.env
```

### Create Required Directories

```bash
# Log directories
sudo mkdir -p /var/log/django /var/log/watchdog
sudo chown psws:psws /var/log/django /var/log/watchdog
sudo chmod 755 /var/log/django /var/log/watchdog

# Static and media directories
mkdir -p /srv/PSWS-Network/static
mkdir -p /srv/PSWS-Network/media/plots

# Station data directory
sudo mkdir -p /home/stations
sudo chown psws:psws /home/stations
sudo chmod 750 /home/stations

# Temporary directory
mkdir -p /psws/temp/ziptemp
```

### Database Initialization

```bash
# Load environment
export DJANGO_SETTINGS_MODULE=psws.settings.prod
source deploy/env/psws.env

# Add src to Python path
export PYTHONPATH=/srv/PSWS-Network/src

# Run migrations
cd /srv/PSWS-Network/src
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Load initial data (instrument types, frequencies)
python manage.py shell < ../scripts/load_initial_data.py
```

### Test Application

```bash
# Test with development server
python manage.py runserver 0.0.0.0:8000

# Access from browser: http://server-ip:8000
# Ctrl+C to stop
```

## Gunicorn Configuration

### Create Gunicorn Service File

```bash
sudo nano /etc/systemd/system/psws-gunicorn.service
```

```ini
[Unit]
Description=PSWS-Network Gunicorn daemon
After=network.target mariadb.service
Requires=mariadb.service

[Service]
Type=notify
User=psws
Group=psws
WorkingDirectory=/srv/PSWS-Network/src
EnvironmentFile=/srv/PSWS-Network/deploy/env/psws.env
Environment="PATH=/srv/PSWS-Network/venv312/bin"
Environment="PYTHONPATH=/srv/PSWS-Network/src"

ExecStart=/srv/PSWS-Network/venv312/bin/gunicorn \
    --workers 4 \
    --worker-class gthread \
    --threads 2 \
    --timeout 120 \
    --bind unix:/srv/PSWS-Network/gunicorn.sock \
    --access-logfile /var/log/django/gunicorn_access.log \
    --error-logfile /var/log/django/gunicorn_error.log \
    --log-level info \
    psws.wsgi:application

ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Worker Configuration:**

Calculate workers: `(2 × CPU cores) + 1`

For a 4-core server: `(2 × 4) + 1 = 9` workers

Adjust `--workers` parameter accordingly.

### Enable and Start Gunicorn

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable psws-gunicorn

# Start service
sudo systemctl start psws-gunicorn

# Check status
sudo systemctl status psws-gunicorn

# View logs
sudo journalctl -u psws-gunicorn -f
```

### Verify Socket

```bash
ls -la /srv/PSWS-Network/gunicorn.sock

# Should show:
# srwxrwxrwx 1 psws psws 0 Feb 16 10:00 gunicorn.sock
```

## Nginx Configuration

### Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/psws
```

```nginx
upstream psws_app {
    server unix:/srv/PSWS-Network/gunicorn.sock fail_timeout=0;
}

server {
    listen 80;
    server_name pswsnetwork.eng.ua.edu;
    
    # Redirect to HTTPS (will be configured by certbot)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name pswsnetwork.eng.ua.edu;
    
    # SSL certificates (will be configured by certbot)
    # ssl_certificate /etc/letsencrypt/live/pswsnetwork.eng.ua.edu/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/pswsnetwork.eng.ua.edu/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Logging
    access_log /var/log/nginx/psws_access.log;
    error_log /var/log/nginx/psws_error.log;
    
    # Max upload size
    client_max_body_size 500M;
    client_body_timeout 300s;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml font/truetype font/opentype application/vnd.ms-fontobject image/svg+xml;
    
    # Static files
    location /static/ {
        alias /srv/PSWS-Network/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    
    # Media files (plots, uploads)
    location /media/ {
        alias /srv/PSWS-Network/media/;
        expires 7d;
        add_header Cache-Control "public";
    }
    
    # Favicon
    location /favicon.ico {
        alias /srv/PSWS-Network/static/img/favicon.ico;
        access_log off;
        log_not_found off;
    }
    
    # Proxy to Gunicorn
    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        proxy_pass http://psws_app;
        proxy_redirect off;
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### Enable Nginx Site

```bash
# Test configuration
sudo nginx -t

# Enable site
sudo ln -s /etc/nginx/sites-available/psws /etc/nginx/sites-enabled/

# Disable default site
sudo rm /etc/nginx/sites-enabled/default

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## SSL Setup

### Let's Encrypt Certificate

```bash
# Obtain certificate (Nginx plugin will auto-configure)
sudo certbot --nginx -d pswsnetwork.eng.ua.edu

# Follow prompts:
# - Enter email address
# - Agree to terms
# - Choose redirect option (2)

# Test auto-renewal
sudo certbot renew --dry-run

# Auto-renewal is configured via systemd timer
sudo systemctl status certbot.timer
```

### Manual SSL Renewal

```bash
# Renew certificates
sudo certbot renew

# Reload Nginx
sudo systemctl reload nginx
```

### Custom SSL Certificate

If using commercial certificate:

```bash
# Copy certificate files
sudo mkdir -p /etc/ssl/psws
sudo cp fullchain.pem /etc/ssl/psws/
sudo cp privkey.pem /etc/ssl/psws/
sudo chmod 600 /etc/ssl/psws/privkey.pem

# Update Nginx configuration
sudo nano /etc/nginx/sites-available/psws
```

```nginx
ssl_certificate /etc/ssl/psws/fullchain.pem;
ssl_certificate_key /etc/ssl/psws/privkey.pem;
```

## Watchdog Service

The watchdog monitors for new data uploads and triggers processing.

### Create Watchdog Service

```bash
sudo nano /etc/systemd/system/psws-watchdog.service
```

```ini
[Unit]
Description=PSWS-Network Watchdog Service
After=network.target mariadb.service psws-gunicorn.service
Requires=mariadb.service

[Service]
Type=simple
User=psws
Group=psws
WorkingDirectory=/srv/PSWS-Network/scripts/watchers
EnvironmentFile=/srv/PSWS-Network/scripts/scripts.env
Environment="PATH=/srv/PSWS-Network/venv312/bin"
Environment="PYTHONPATH=/srv/PSWS-Network/src"
Environment="DJANGO_SETTINGS_MODULE=psws.settings.prod"

ExecStart=/srv/PSWS-Network/venv312/bin/python psws_watch10.py

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Configure Watchdog Environment

```bash
cd /srv/PSWS-Network/scripts
cp scripts.env.example scripts.env
nano scripts.env
```

```bash
LOG_PATH=/var/log/watchdog/watchdog.log
PYTHON_EXECUTABLE=/srv/PSWS-Network/venv312/bin/python3
PLOT_PATH=/srv/PSWS-Network/media/plots
DJANGO_SETTINGS_MODULE=psws.settings.prod
PYTHONPATH=/srv/PSWS-Network/src
```

### Enable Watchdog

```bash
sudo systemctl daemon-reload
sudo systemctl enable psws-watchdog
sudo systemctl start psws-watchdog
sudo systemctl status psws-watchdog

# View logs
tail -f /var/log/watchdog/watchdog.log
```

## Post-Deployment

### Verify Services

```bash
# Check all services
sudo systemctl status mariadb
sudo systemctl status psws-gunicorn
sudo systemctl status nginx
sudo systemctl status psws-watchdog
sudo systemctl status certbot.timer
```

### Test Application

1. **Web Interface**: https://pswsnetwork.eng.ua.edu
2. **Admin Interface**: https://pswsnetwork.eng.ua.edu/admin/
3. **API Endpoint**: https://pswsnetwork.eng.ua.edu/api/stations/

### Create Initial Data

```bash
cd /srv/PSWS-Network/src
source ../venv312/bin/activate
export DJANGO_SETTINGS_MODULE=psws.settings.prod

python manage.py shell
```

```python
# Create instrument types
from apps.instrumenttypes.models import InstrumentType
InstrumentType.objects.get_or_create(instrumentType='Grape 1 Legacy')
InstrumentType.objects.get_or_create(instrumentType='Grape 1 DRF')
InstrumentType.objects.get_or_create(instrumentType='Magnetometer')
InstrumentType.objects.get_or_create(instrumentType='TangerineSDR')

# Create center frequencies
from apps.centerfrequencies.models import CenterFrequency
for freq in [2.5, 3.33, 5.0, 7.85, 10.0, 14.67, 15.0, 20.0, 25.0]:
    CenterFrequency.objects.get_or_create(centerFrequency=freq)

exit()
```

### Configure Log Rotation

```bash
sudo nano /etc/logrotate.d/psws
```

```
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
        systemctl reload psws-gunicorn > /dev/null 2>&1 || true
    endscript
}

/var/log/watchdog/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 psws psws
    sharedscripts
    postrotate
        systemctl reload psws-watchdog > /dev/null 2>&1 || true
    endscript
}
```

### Set Up Backups

See [ADMIN.md](../docs/ADMIN.md#backup-and-recovery) for backup procedures.

## Monitoring

### Health Check Script

```bash
nano /usr/local/bin/psws_health_check.sh
```

```bash
#!/bin/bash

echo "=== PSWS-Network Health Check ==="
echo "Date: $(date)"
echo ""

# Check services
echo "Services:"
systemctl is-active mariadb && echo "  MariaDB: OK" || echo "  MariaDB: FAILED"
systemctl is-active psws-gunicorn && echo "  Gunicorn: OK" || echo "  Gunicorn: FAILED"
systemctl is-active nginx && echo "  Nginx: OK" || echo "  Nginx: FAILED"
systemctl is-active psws-watchdog && echo "  Watchdog: OK" || echo "  Watchdog: FAILED"
echo ""

# Check disk space
echo "Disk Usage:"
df -h | grep -E '^Filesystem|/dev/vda|/dev/sda'
echo ""

# Check database
echo "Database Status:"
mysql -u psws_user -p'password' psws_db -e "SELECT COUNT(*) as Stations FROM stations_station;" 2>/dev/null && echo "  Connection: OK" || echo "  Connection: FAILED"
echo ""

# Check application
echo "Application Status:"
curl -s -o /dev/null -w "  HTTP Response: %{http_code}\n" https://pswsnetwork.eng.ua.edu
```

```bash
chmod +x /usr/local/bin/psws_health_check.sh
```

### Monitoring Cron

```bash
crontab -e
```

```
# Health check every hour
0 * * * * /usr/local/bin/psws_health_check.sh >> /var/log/psws_health.log 2>&1
```

## Updates

### Application Updates

```bash
# Switch to psws user
sudo su - psws
cd /srv/PSWS-Network

# Backup current version
cp -r /srv/PSWS-Network /srv/PSWS-Network.backup.$(date +%Y%m%d)

# Pull updates
git pull origin main

# Activate virtual environment
source venv312/bin/activate

# Update dependencies
pip install -r requirements.txt

# Run migrations
cd src
export DJANGO_SETTINGS_MODULE=psws.settings.prod
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart psws-gunicorn
sudo systemctl reload nginx
sudo systemctl restart psws-watchdog
```

### Zero-Downtime Deployment

```bash
# Use Gunicorn graceful reload
sudo systemctl reload psws-gunicorn

# Or send HUP signal
sudo kill -HUP $(cat /run/psws-gunicorn.pid)
```

## Troubleshooting

### View Logs

```bash
# Gunicorn logs
sudo journalctl -u psws-gunicorn -f
tail -f /var/log/django/gunicorn_error.log

# Nginx logs
sudo tail -f /var/log/nginx/psws_error.log

# Django logs
tail -f /var/log/django/django.log

# Watchdog logs
tail -f /var/log/watchdog/watchdog.log
```

### Common Issues

**502 Bad Gateway:**
- Check Gunicorn is running: `sudo systemctl status psws-gunicorn`
- Check socket permissions: `ls -la /srv/PSWS-Network/gunicorn.sock`
- Review Gunicorn logs

**Static Files Not Loading:**
- Run: `python manage.py collectstatic --clear --noinput`
- Check Nginx configuration and file permissions

**Database Connection Errors:**
- Verify MariaDB is running: `sudo systemctl status mariadb`
- Check credentials in `psws.env`
- Test connection: `mysql -u psws_user -p psws_db`

## Rollback Procedure

If deployment fails:

```bash
# Stop services
sudo systemctl stop psws-gunicorn psws-watchdog

# Restore from backup
sudo rm -rf /srv/PSWS-Network
sudo cp -r /srv/PSWS-Network.backup.YYYYMMDD /srv/PSWS-Network
sudo chown -R psws:psws /srv/PSWS-Network

# Restore database (if needed)
mysql -u psws_user -p psws_db < /var/backups/psws/db_backup.sql

# Restart services
sudo systemctl start psws-gunicorn psws-watchdog
```

## Security Hardening

See [SECURITY.md](../docs/SECURITY.md) for comprehensive security configuration.

## Support

For deployment assistance:
- Email: bill.engelke@cs.ua.edu
- Documentation: https://github.com/yourusername/PSWS-Network/wiki
