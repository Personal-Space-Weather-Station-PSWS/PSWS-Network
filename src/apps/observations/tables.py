# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import django_tables2 as tables
from .models import Observation
from django_tables2 import A

class TruncatedTextColumn(tables.Column):
    """ Custom Column class derived from django_tables2 Column class """

    def render(self, value):
        """ Limits the length of the Instrument Name
        Parameters
        ----------
        value : string | len < 41
            Instrument name corresponding to the Observation.
        Returns
        -------
        value : string
            Instrument name truncated to length 15 with '...' added
            to signify that the Instument name is longer than shown
            in the observation table if and only if the instument name
            was orginally of length greater than 15. 
        """  

        if len(value) > 15:
            # returns first 15 chars of instrument name. Appends '...' to end
            return value[0:15] + '...'
        return str(value)

class PlotColumn(tables.BooleanColumn):
    """ Custom  Boolean Column class derived from django_tables2 BooleanColumn class."""

    def render(self, value):
        """ Determines boolean value for if Observation Plot File exists
        Parameters
        ----------
        value : string | len < 41
            Holds plot filename associated with current observation within database.
        Returns
        -------
        response : char
           If condiational returns true, repsones is fed the python unicode for a green
           dot to appear in the column, where as if the condition returns false, response 
           returns an empty string to display.
        """
        response= ''
        if value != None:
           response= '\U0001F7E2'
           return response
        return response

class ObservationTable(tables.Table):
    size = tables.Column(verbose_name='Size (MB)')
    fileName = tables.LinkColumn('select_download_range', args=[A('id')], verbose_name='File/Observation')
    startDate = tables.DateTimeColumn(format="Y-m-d H:i:s", verbose_name="Start (UTC)")
    endDate   = tables.DateTimeColumn(format="Y-m-d H:i:s", verbose_name="End (UTC)")
    instrument = TruncatedTextColumn(accessor=A('instrument.instrument'))
    plotExists = PlotColumn(accessor=A('plotFile'), verbose_name="Plot")

    # Make station a clickable link to its homepage
    station = tables.LinkColumn(
        'station_analysis', 
        args=[A('station.id')], 
        verbose_name='Station'
    )

    def render_size(self, value):
        converted_size = float(value)
        converted_size = converted_size / 1000000.0
        return "{:,.4f}".format(converted_size)
        #return "%s MB" % converted_size / 1000000.0

    class Meta:
        model = Observation
        template_name = "django_tables2/bootstrap.html"
        fields = ("dataRate", "centerFrequency", "station", "instrument", "size", "fileName", "plotExists", "startDate", "endDate")
        attrs = {"class": "obsTable"}
        
