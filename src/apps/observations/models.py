# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.db import models

from apps.stations.models import Station
from apps.instruments.models import Instrument
from apps.bands.models import Band
from apps.datatypes.models import DataType
from apps.centerfrequencies.models import CenterFrequency
from apps.producttypes.models import ProductType
from apps.fileformats.models import FileFormat
from apps.filestatuses.models import FileStatus

class Observation(models.Model):
    #
    dataType = models.ManyToManyField(DataType, verbose_name="Data type", blank=True)
    # Number of samples per second recorded from instrument
    dataRate = models.IntegerField("Data rate")
    # Center Frequency retreived from centerfrequencies.models
    centerFrequency = models.ManyToManyField(CenterFrequency, verbose_name="Center Frequency", blank=True)
    # Station Name retrieved from stations.models
    station = models.ForeignKey(Station, on_delete=models.CASCADE, null=True)
    # Instrument Type retreived from instruments.models
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, default=1)
    #
    band = models.ManyToManyField(Band, verbose_name="Band", blank=True)
    #
    size = models.BigIntegerField()
    # Observation filename
    fileName = models.CharField("File", max_length=60)
    # Observation plot filename
    plotFile = models.CharField("Plot", max_length=60, null=True, blank=True)
    # Directory to which all Observation data is stored via schema - /home/"station_name"/"observation_filename"
    path = models.CharField(max_length=60)
    # Directory to which the observation plot is stored via schema - /home/plots
    plotPath = models.CharField(max_length=40, null=True, blank=True)
    # Timestamp from which the observation started for the given time period
    startDate = models.DateTimeField("Start Date (UTC)")
    # Timestamp from which the observation ended for the given time period
    endDate = models.DateTimeField("End Date (UTC)", null=True, blank=True)

    def __str__(self):
        return 'Observation_' + self.station.station_id + '_' + self.fileName


class DataProduct(models.Model):
    observation = models.ForeignKey(Observation, on_delete=models.CASCADE)
    path = models.CharField(max_length=60)
    fileName = models.CharField(max_length=60)
    dataType = models.ForeignKey(DataType, on_delete=models.CASCADE)
    size = models.BigIntegerField()
    created_by = models.CharField(max_length=40, null=True, blank=True)
    created_by_program = models.CharField(max_length=20, null=True, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    productType = models.ForeignKey(ProductType, on_delete=models.CASCADE)
    description = models.CharField(max_length=80, null=True, blank=True)
    fileFormat = models.ForeignKey(FileFormat, on_delete=models.CASCADE)
    tags = models.CharField(max_length=40, null=True, blank=True)
    DOI = models.CharField(max_length=40, null=True, blank=True)
    Notes = models.CharField(max_length=80, null=True, blank=True)
    fileStatus = models.ForeignKey(FileStatus, on_delete=models.CASCADE)

    def __str__(self):
        return 'DataProduct_' + str(self.observation.id) + '_' + self.fileName
