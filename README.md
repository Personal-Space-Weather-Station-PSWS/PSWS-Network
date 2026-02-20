# PSWS-Network

Personal Space Weather Station Network - Central Control System

## Overview

The PSWS-Network is a Django-based web application that serves as the central control system for a distributed network of space weather monitoring stations. The system enables crowd-sourced collection of radio spectrum data for ionospheric research while providing useful propagation monitoring tools for amateur radio operators and shortwave listeners.

## Mission

The Personal Space Weather Network (PSWN) has a dual mission:

1. **Scientific Research**: Crowd-source radio spectrum data collection for ionospheric research
2. **Amateur Radio Support**: Provide useful instruments for radio amateurs and shortwave listeners to observe radio propagation conditions at their locations

## Key Features

- **Station Management**: Register and manage space weather monitoring stations
- **Instrument Tracking**: Support for multiple instrument types (Grape SDR, TangerineSDR, Magnetometers)
- **Data Collection**: Automated ingestion of spectrum observations and magnetometer data
- **Real-time Monitoring**: Track station status with heartbeat monitoring
- **Data Visualization**: Generate plots and graphs from collected observations
- **Public API**: Download observations programmatically with geographic and temporal filtering
- **Analysis Tools**: Magnetometer data analysis and visualization
- **User Authentication**: Secure user accounts with email verification

## Technology Stack

- **Framework**: Django 4.2.27
- **Database**: MariaDB/MySQL
- **Python**: 3.12+
- **Web Server**: Gunicorn + Nginx
- **Key Libraries**:
  - Django REST Framework for API
  - django-tables2 for data tables
  - django-filters for observation filtering
  - digital_rf for Digital RF data handling
  - matplotlib/plotly for visualization
  - astropy for astronomical calculations

## System Architecture

The system consists of:

1. **Web Application** (Django): User interface, station/observation management
2. **REST API**: Programmatic access to observations and station data
3. **Watchdog Service**: Monitors for new data uploads and triggers processing
4. **Plotting Scripts**: Generate visualizations from observation data
5. **Database**: Stores stations, instruments, observations, and user data

## Quick Links

- [Installation Guide](docs/QUICKSTART.md)
- [Backend Documentation](docs/BACKEND.md)
- [Frontend Documentation](docs/FRONTEND.md)
- [Security Documentation](docs/SECURITY.md)
- [Admin Guide](docs/ADMIN.md)
- [Deployment Guide](deploy/README.md)

## Project Structure

```
PSWS-Network/
├── deploy/              # Deployment configurations
│   ├── env/            # Environment variable templates
│   ├── gunicorn/       # Gunicorn service configuration
│   └── nginx/          # Nginx configuration
├── docs/               # Documentation
├── scripts/            # Utility scripts
│   ├── audit/          # Database/filesystem audit tools
│   ├── ingest/         # Data ingestion scripts
│   ├── plotters/       # Visualization scripts
│   ├── triggers/       # Trigger file manipulation
│   └── watchers/       # Watchdog file monitoring
├── src/                # Django application source
│   ├── apps/           # Django applications
│   └── psws/           # Project configuration
├── manage.py           # Django management script
└── requirements.txt    # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.12 or higher
- MariaDB/MySQL database
- Git
- Virtual environment tool (venv/virtualenv)

### Installation

See [QUICKSTART.md](docs/QUICKSTART.md) for detailed installation instructions.

Quick setup:

```bash
# Clone the repository
git clone https://github.com/yourusername/PSWS-Network.git
cd PSWS-Network

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp deploy/env/psws.env.example deploy/env/psws.env
# Edit psws.env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

## Supported Instruments

### Grape SDR (v1 & v2)
Low-cost software-defined radio for spectrum observation around 1-4 center frequencies.

### TangerineSDR
High-precision SDR supporting up to 8 center frequencies plus FT8/WSPR channels.

### Magnetometer
Ground-based magnetometer systems for measuring Earth's magnetic field variations.

## Data Types

The system supports multiple observation types:

- **Spectrum Data**: Digital RF format recordings
- **CSV Data**: Grape 1 Legacy format
- **Magnetometer Data**: JSON/CSV magnetic field measurements

## Contributing

This project is maintained by the University of Alabama's Digital Forensics and Control Systems Security Lab (DCSL). Contributions are welcome!

## License

Distributed under the BSD 3-Clause License. See `LICENSE` file for details.

## Copyright

Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)

## Funding

This project is sponsored by the National Science Foundation (NSF Grant 80NSSC21K1772).

## Contact

For questions or support:
- Email: bill.engelke@cs.ua.edu
- Project Website: https://pswsnetwork.eng.ua.edu

## Acknowledgments

- HamSCI (Ham Radio Science Citizen Investigation)
- TAPR (Tucson Amateur Packet Radio)
- Case Western Reserve University (Grape SDR)
- All contributing station operators

## Related Links

- [TangerineSDR Documentation](https://tangerinesdr.com/)
- [Grape SDR Information](https://hamsci.org/grape1)
- [HamSCI Project Page](https://hamsci.org/basic-project/personal-space-weather-station)
