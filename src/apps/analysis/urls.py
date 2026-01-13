# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.urls import path
from . import views
from core.views import under_construction

urlpatterns = [
        # path('line_plot/', views.line_plot, name='line_plot'),
        path('analysis/', views.analysis_map, name='analysis_map'),
        # path to display graphs
        path('analysis/display_graphs/', under_construction, name='display_graphs'),
        # do we need next anymore?
        path('analysis/station_analysis/<int:id>/', under_construction, name='station_analysis'),
        ]
   
