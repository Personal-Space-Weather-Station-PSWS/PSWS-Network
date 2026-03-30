# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import os
import django
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'manage.settings')
django.setup()

from django.contrib.auth.models import User
from src.apps.stations.models import Station

def audit_wwv_users():
    print(f"{'Username':<20} | {'Email':<30} | {'Legacy Station Count'}")
    print("-" * 70)
    
    users = User.objects.all()
    for user in users:
        legacy_stations = Station.objects.filter(owner=user, ingestion_format='WWV')
        if legacy_stations.exists():
            print(f"{user.username:<20} | {user.email:<30} | {legacy_stations.count()}")

if __name__ == "__main__":
    try:
        audit_wwv_users()
    except Exception as e:
        print(f"Audit failed: {e}")
        sys.exit(1)