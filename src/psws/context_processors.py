# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.conf import settings

def psws_public_settings(request):
    return {
        "MAPBOX_ACCESS_TOKEN": getattr(settings, "MAPBOX_ACCESS_TOKEN", ""),
    }
