# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.contrib import admin
from django.urls import path, include
from django.views.generic.base import RedirectView
from apps.api import views as apiviews
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

favicon_view = RedirectView.as_view(url= settings.BASE_DIR /'static/img/favicon.ico', permanent=True)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('stations/', apiviews.StationList.as_view(), name='stationList'),
    path('heartbeat/', apiviews.StationHeartbeat.as_view(), name='heartbeat'),
    path('stop/', apiviews.StationStop.as_view(), name='stop'),
    path('accounts/', include('apps.accounts.urls')),
    path('', include('apps.accounts.urls')),
    path('stations/', include('apps.stations.urls')),
    path('favicon.ico', favicon_view),
    path('observations/', include('apps.observations.urls')),
    path('instruments/', include('apps.instruments.urls')),
    path('analysis/', include('apps.analysis.urls')),
    path("", include("apps.core.urls")),
] +  staticfiles_urlpatterns()
