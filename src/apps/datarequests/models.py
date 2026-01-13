# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.db import models
from accounts.models import Profile

# Create your models here.
class DataRequest(models.Model):
    requestID = models.AutoField(primary_key=True)
    timestart = models.DateTimeField()
    timestop = models.DateTimeField()
    requester = models.ManyToManyField(Profile)
