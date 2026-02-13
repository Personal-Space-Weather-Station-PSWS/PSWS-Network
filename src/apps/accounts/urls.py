# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.conf.urls import include
from django.contrib.auth import views as auth_views
from django.contrib.auth import urls
from django.urls import path
from . import views
from .views import UserListView 
from apps.core.views import under_construction

urlpatterns = [
    path('', include('django.contrib.auth.urls')),
    path('profile/', views.profile, name='profile'),
    path('', views.home, name='home'),
    path('home', views.home, name='home'),
    path('signup/', views.signup_view, name="signup"),
    path('sent/', views.activation_sent_view, name="activation_sent"),
    path('activate/<slug:uidb64>/<slug:token>/', views.activate, name='activate'),
    path('user_list/', UserListView.as_view(), name="user_list"),
    path('about/', views.about_view, name="about"),
    path('about1/', views.about1_view, name="about1"),
    path('station_analysis/<int:id>/', under_construction, name='station_analysis'),
]
