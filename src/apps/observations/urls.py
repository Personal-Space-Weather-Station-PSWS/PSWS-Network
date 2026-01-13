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
from .views import ObservationListView
from .apiviews import ObservationDownloadAPIView

urlpatterns = [
        path('observation_list/', ObservationListView.as_view(), name="observation_list"),
        path('download/<int:id>/', views.download_file, name='download_file'),
        path('downloadplot/<int:id>/', views.download_plot, name='download_plot'),
        path('download/<int:id>/', views.download_range, name='download_range'),
        path('range/<int:id>/', views.get_date_range, name='get_date_range'),
        path('select_download_range/<int:id>/', views.select_download_range, name='select_download_range'),
        path('download_range/<int:id>/', views.download_range, name='download_range'),
        path('downloadapi/', ObservationDownloadAPIView.as_view(), name='observation-download'),
        ]
