# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import django_tables2 as tables
from .models import Instrument
from django_tables2 import A
from django_tables2.utils import Accessor
from apps.instrumenttypes.models import InstrumentType

class InstrumentTable(tables.Table):
   # id = tables.LinkColumn('instrument_details', args=[A('station_id')])
    id =  tables.LinkColumn('instrument_details', args=[A('id')])
    instrument_type = tables.Column(accessor=Accessor('instrumenttype.instrumentType'))

    class Meta:
        model = Instrument
        template_name = "django_tables2/bootstrap.html"
        fields = ("id", "instrument", "nickname", "serialNo",
           "instrument_type" )

#
class FilteredInstrumentsTable (tables.Table):  # used for display after adding new intrument
    id = tables.LinkColumn('instrument_details', args=[A('station_id')])

    class Meta:
        model = Instrument
        template_name = "django_tables2/bootstrap.html"
        field = ("id", "instrument",  "instrumenttype_id", "nickname", "serialNo", "status", "status", )

