# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from rest_framework import serializers
from apps.stations.models import Station
from apps.observations.models import Observation

class StationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ['user', 'nickname', 'station_status', 'station_id', 'last_alive']

class HeartbeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ['nickname', 'station_id', 'station_pass']

class StationStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Station
        fields = ['station_id', 'station_pass']
