# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.db import models

# Create your models here.
class CenterFrequency(models.Model):
    centerFrequency = models.DecimalField(max_digits = 5, decimal_places = 3, verbose_name="Center Frequency (MHz)")
    
    def __str__(self):
       return str(self.centerFrequency) + ' MHz' 

    class Meta:
        verbose_name = 'Center Frequency (MHz)'
        verbose_name_plural = 'Center Frequencies (MHz)'
