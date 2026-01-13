# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.urls import path, re_path
from . import views
from .views import InstrumentListView

urlpatterns = [
        path('instruments/', views.InstrumentListView, name = "instruments"),
        path('add/', views.add_instrument_view, name="add_instrument"),
        path('add/<int:id>/', views.add_instrument_view, name = "add_instrument"),
        path('downloadconfig/<int:id>/', views.download_config, name='download_config'),
        path('update/<int:id>/', views.update_instrument_view, name="instrument_update"),
        path('instrument_details/<int:id>/', views.instrument_details_view, name="instrument_details"),
        ]

