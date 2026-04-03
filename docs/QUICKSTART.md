# PSWS-Network Quick Start Guide

This guide will help you get the PSWS-Network up and running quickly.

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 24 LTS (recommended) or similar Linux distribution
- **Python**: 3.12 or higher
- **Database**: MariaDB 10.5+ or MySQL 8.0+
- **Memory**: Minimum 4GB RAM (8GB+ recommended)
- **Storage**: Minimum 100GB (depends on observation data volume)

### Required Software

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3.12 python3.12-venv python3-pip python3-dev

# Install MariaDB
sudo apt install mariadb-server mariadb-client

# Install build tools
sudo apt install build-essential libssl-dev libffi-dev

# Install system libraries for scientific computing
sudo apt install libhdf5-dev libnetcdf-dev
```

## Installation

### 1. Clone the Repository

```bash
cd /srv
sudo git clone https://github.com/yourusername/PSWS-Network.git
sudo chown -R $USER:$USER /srv/PSWS-Network
cd /srv/PSWS-Network
```

### 2. Create Virtual Environment

```bash
python3.12 -m venv venv312
source venv312/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Database

```bash
# Secure MariaDB installation
sudo mysql_secure_installation

# Create database and user
sudo mysql -u root -p
```

In the MySQL prompt:

```sql
CREATE DATABASE psws_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'psws_user'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON psws_db.* TO 'psws_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. Configure Environment Variables

```bash
# Copy environment template
cp deploy/env/psws.env.example deploy/env/psws.env

# Edit configuration
nano deploy/env/psws.env
```

**Minimum Required Configuration:**

```bash
# Django Core
DJANGO_SECRET_KEY="your-secret-key-here-generate-with-django"
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=your.domain.com,localhost

# Database
PSWS_DB_NAME=psws_db
PSWS_DB_USER=psws_user
PSWS_DB_PASSWORD=your_secure_password
PSWS_DB_HOST=localhost
PSWS_DB_PORT=3306

# External Services
MAPBOX_ACCESS_TOKEN="your-mapbox-token"

# Paths
ACCOUNT_ACTIVATION_LOG_PATH=/var/log/django/
```

**Generate Secret Key:**

```bash
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### 6. Initialize Database

```bash
# Set Django settings
export DJANGO_SETTINGS_MODULE=psws.settings.dev

# Add src to Python path
export PYTHONPATH=/srv/PSWS-Network/src

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 7. Create Required Directories

```bash
# Create log directories
sudo mkdir -p /var/log/django /var/log/watchdog
sudo chown -R $USER:$USER /var/log/django /var/log/watchdog

# Create media/plots directory
mkdir -p media/plots

# Create station data directory
sudo mkdir -p /home/stations
sudo chown -R $USER:$USER /home/stations

# Create temporary zip directory
mkdir -p /psws/temp/ziptemp
```

### 8. Load Initial Data

```bash
# Create instrument types
python manage.py shell
```

In Python shell:

```python
from apps.instrumenttypes.models import InstrumentType

InstrumentType.objects.create(instrumentType='Grape 1 Legacy')
InstrumentType.objects.create(instrumentType='Grape 1 DRF')
InstrumentType.objects.create(instrumentType='Magnetometer')
InstrumentType.objects.create(instrumentType='TangerineSDR')
exit()
```

Create center frequencies:

```python
from apps.centerfrequencies.models import CenterFrequency

for freq in [2.5, 3.33, 5.0, 7.85, 10.0, 14.67, 15.0, 20.0, 25.0]:
    CenterFrequency.objects.get_or_create(centerFrequency=freq)
```

### 9. Test Development Server

```bash
python manage.py runserver 0.0.0.0:8000
```

Visit `http://localhost:8000` in your browser.

## Scripts Configuration

### Configure Scripts Environment

```bash
cd scripts
cp .env.example scripts.env
nano scripts.env
```

Edit with your paths:

```bash
LOG_PATH=/var/log/watchdog/watchdog.log
PYTHON_EXECUTABLE=/srv/PSWS-Network/venv312/bin/python3
PLOT_PATH=/srv/PSWS-Network/media/plots
```

## Production Deployment

For production deployment, see [deploy/README.md](../deploy/README.md).

### Quick Production Setup

```bash
# Install Gunicorn (already in requirements.txt)
pip install gunicorn

# Copy and configure Gunicorn service
sudo cp deploy/gunicorn/psws-gunicorn.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable psws-gunicorn
sudo systemctl start psws-gunicorn

# Install and configure Nginx
sudo apt install nginx
sudo cp deploy/nginx/psws.conf /etc/nginx/sites-available/psws
sudo ln -s /etc/nginx/sites-available/psws /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Troubleshooting

### Database Connection Issues

```bash
# Test database connection
python manage.py dbshell
```

If connection fails:
- Verify MariaDB is running: `sudo systemctl status mariadb`
- Check credentials in `psws.env`
- Ensure database exists: `sudo mysql -u root -p -e "SHOW DATABASES;"`

### Permission Errors

```bash
# Fix ownership
sudo chown -R $USER:$USER /srv/PSWS-Network
sudo chown -R $USER:$USER /var/log/django

# Fix permissions
chmod -R 755 /srv/PSWS-Network
```

### Static Files Not Loading

```bash
# Recollect static files
python manage.py collectstatic --clear --noinput

# Check STATIC_ROOT in settings
python manage.py shell -c "from django.conf import settings; print(settings.STATIC_ROOT)"
```

### Import Errors

```bash
# Ensure PYTHONPATH is set
export PYTHONPATH=/srv/PSWS-Network/src

# Or add to manage.py path manipulation
```

## Next Steps

1. **Configure Email**: Set up SMTP settings for user activation emails
2. **Set Up SSL**: Configure SSL certificates for HTTPS
3. **Configure Watchdog**: Set up the file monitoring service
4. **Review Security**: See [SECURITY.md](SECURITY.md)
5. **Admin Configuration**: See [ADMIN.md](ADMIN.md)

## Common Commands

```bash
# Activate virtual environment
source venv312/bin/activate

# Run development server
python manage.py runserver

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell

# Check for problems
python manage.py check

# Run tests
python manage.py test
```

## Getting Help

- Check [BACKEND.md](BACKEND.md) for Django application details
- Check [FRONTEND.md](FRONTEND.md) for UI customization
- Review logs in `/var/log/django/` and `/var/log/watchdog/`
- Contact: bill.engelke@cs.ua.edu
