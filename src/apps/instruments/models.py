# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.db import models

from apps.instrumenttypes.models import InstrumentType
from apps.stations.models import Station

# Create your models here.
class Instrument(models.Model):
    instrument = models.CharField(max_length=40)
    instrumenttype = models.ForeignKey(InstrumentType, on_delete=models.CASCADE, null=True)
    station = models.ForeignKey(Station, on_delete=models.CASCADE, default=1)
    serialNo = models.CharField(max_length=60, null=True, blank=True)
    dateAdded = models.DateTimeField("Date Added", null=True, blank=True)
    dateRemoved = models.DateTimeField("Date Removed", null=True, blank=True)
    status = models.CharField(max_length=10, null=True, blank=True)
    nickname = models.CharField(max_length=40, null=True, blank=True)

    def __str__(self):
        return self.instrument + "\n(" + self.instrumenttype.instrumentType + ")"
