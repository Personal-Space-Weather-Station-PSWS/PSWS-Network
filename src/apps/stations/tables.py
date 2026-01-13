# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import django_tables2 as tables
from .models import Station
from django_tables2 import A
from instruments.models import Instrument

class StationTable(tables.Table):
    class Meta:
        model = Station
        template_name = "django_tables2/bootstrap.html"
        fields = ("station_id", "user", "nickname", "grid", "elevation", "station_status",)

class FilteredStationTable(tables.Table):
    station_id = tables.LinkColumn('station_details', args=[A('id')])

    class Meta:
        model = Station
        template_name = "django_tables2/bootstrap.html"
        fields = ("station_id", "nickname", "grid", "elevation", "antenna_1", "antenna_2", "station_status",)



class StationUserTable(tables.Table):
    user = tables.LinkColumn(
        "station_instruments",       # matches your urls.py name
        args=[tables.A("user.id")],   # sends station.id into <int:id>
        text = lambda record: str(record.user),
        verbose_name="User"
    )

    class Meta:
        model = Station
        template_name = "django_tables2/bootstrap.html"
        fields = ("user", "nickname",)


class StationInstrumentTable(tables.Table):
    user = tables.Column(accessor="station.user.username", verbose_name="User")
    instrument_type = tables.Column(accessor="instrumenttype.instrumentType", verbose_name="Instrument Type")

    class Meta:
        model = Instrument
        template_name = "django_tables2/bootstrap.html"
        fields = ("user", "station", "instrument_type")
