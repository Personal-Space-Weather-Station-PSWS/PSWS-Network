# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import datetime

# Create your models here.

class Station(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    station_id = models.CharField("ID", max_length=10, default='N000000')
    station_pass = models.CharField(max_length=32, null=True, blank=True)
    nickname = models.CharField(max_length=50)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    grid = models.CharField(max_length=6, null=True)
    elevation = models.FloatField(blank=True, null=True) 
    antenna_1 = models.CharField(max_length=64, null=True) 
    antenna_2 = models.CharField(max_length=64, blank=True)
    street_address = models.CharField(max_length=75, blank=True)
    city = models.CharField(max_length=75, blank=True)
    state = models.CharField(max_length=15, blank=True)
    postal_code = models.CharField(max_length=15, blank=True) #must support international values
    phone_number = models.CharField(max_length=20, blank=True)
    create_date = models.DateTimeField(auto_now_add=True)

    last_rID = models.IntegerField(default=0)
    last_alive = models.DateTimeField(null=True)

    offlineNotify = models.BooleanField("Station Offline Notification", null=True, blank=True)

    class StationStatus(models.TextChoices):
           ONLINE =  "Online",
           POSSIBLYONLINE =  "PossiblyOnline",
           OFFLINE =  "Offline"
    
    station_status = models.CharField(
            max_length=20,
            choices=StationStatus.choices,
            default=StationStatus.OFFLINE,
    )

    def __str__(self):
        return self.nickname


