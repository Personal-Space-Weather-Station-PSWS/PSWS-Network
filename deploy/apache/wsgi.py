# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import os
import sys
from pathlib import Path

# Resolve repo root from this file location:
# repo_root/deploy/apache/wsgi.py -> parents[2] = repo_root
REPO_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_DIR / "src"

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.environ.get("DJANGO_SETTINGS_MODULE", "psws.settings.prod"),
)

from django.core.wsgi import get_wsgi_application  # noqa: E402
application = get_wsgi_application()
