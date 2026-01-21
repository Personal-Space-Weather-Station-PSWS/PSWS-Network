# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.sites.shortcuts import get_current_site
from django.utils.encoding import force_str, force_bytes
from django.db import IntegrityError
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.views.generic.edit import UpdateView
from django.utils.decorators import method_decorator
from django_tables2 import SingleTableView



from .forms import SignUpForm, EditProfileForm
from .tokens import account_activation_token
from .models import Profile
from .tables import UserTable
from apps.stations.models import Station

from apps.observations.models import Observation
from apps.observations.tables import ObservationTable
from apps.instruments.models import Instrument

import logging
logger = logging.getLogger(__name__)

from datetime import datetime, timedelta, timezone

# Station Status Cutoffs
ONLINE_CUT_OFF_HOURS = settings.ONLINE_CUT_OFF_HOURS
POSSIBLY_ONLINE_CUT_OFF_HOURS = settings.POSSIBLY_ONLINE_CUT_OFF_HOURS
RETIREMENT_CUT_OFF_HOURS = settings.RETIREMENT_CUT_OFF_HOURS

# Activation Log Path
ACCOUNT_ACTIVATION_LOG_PATH=settings.ACCOUNT_ACTIVATION_LOG_PATH


def updateStatus():
    #Update Station status of all stations before displaying
    AliveCutoff = datetime.now(timezone.utc) - timedelta(hours=ONLINE_CUT_OFF_HOURS)
    DeadCutoff = datetime.now(timezone.utc) - timedelta(hours=POSSIBLY_ONLINE_CUT_OFF_HOURS)
    RetiredCutoff = datetime.now(timezone.utc) - timedelta(hours=RETIREMENT_CUT_OFF_HOURS)

    for instance in Station.objects.all():
        if (instance.last_alive is None):
            instance.last_alive = datetime(2000,1,1,tzinfo=timezone.utc)
        if (instance.last_alive < RetiredCutoff):
            instance.station_status = "Retired"
        elif (instance.last_alive < DeadCutoff):
            instance.station_status = "Offline"
        elif (instance.last_alive < AliveCutoff):
            instance.station_status = "PossiblyOnline"
        else:
            instance.station_status = "Online"
       # if station has never submitted an upload, they are marked inactive and won't show on map
        if (instance.last_alive == datetime(2000,1,1,tzinfo=timezone.utc)):
            instance.station_status = "Inactive"
        instance.save()

def home(request):
    updateStatus()
    online_stations = Station.objects.filter(station_status="Online") 
    possiblyonline_stations = Station.objects.filter(station_status="PossiblyOnline")
    offline_stations = Station.objects.filter(station_status="Offline")
    retired_stations = Station.objects.filter(station_status="Retired")

    return render(request, 'home.html',
      { 'mapbox_access_token' : settings.MAPBOX_ACCESS_TOKEN,
          'online_stations' : online_stations,
          'possiblyonline_stations' : possiblyonline_stations,
          'offline_stations' : offline_stations,
	        'retired_stations' : retired_stations,
        } )

@login_required
def profile(request):
    if request.method == 'POST':
        logger.error("POST request received")
        p_form = EditProfileForm(request.POST, instance=request.user.profile)
        if p_form.is_valid():
            logger.error(request.user.profile.email)
            request.user.profile.email = p_form.cleaned_data.get('email')
            request.user.profile.save()
            messages.success(request, 'Your Profile has been updated!')
            return redirect('profile')
        else:
            p_form = EditProfileForm(instance=request.user)
            messages.error(request, 'Issue updating information.')

        context={'p_form': p_form}
        return render(request, 'profile.html',context )
    else:
        p_form = EditProfileForm()
        return render(request, 'profile.html', {'p_form': p_form})

def activation_sent_view(request):
    return render(request, 'activation_sent.html')

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        ######
        f = open(ACCOUNT_ACTIVATION_LOG_PATH + "account.log", "a")
        f.write(str(user) + "\n")
        f.write(str(token) + "\n")
        f.close()
        ######
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as ex:
        user = None
        ######
        f = open(ACCOUNT_ACTIVATION_LOG_PATH + "account.log", "a")
        f.write(str(ex) + "\n")
        f.close()
        ######
    # checking if the user exists, if the token is valid.
    f = open(ACCOUNT_ACTIVATION_LOG_PATH + "account.log", "a")
    f.write("Account token: " + str(account_activation_token.check_token(user, token)) + "\n")
    f.close()
    if user is not None and account_activation_token.check_token(user, token):
        # if valid set active true 
        user.is_active = 1
        # set signup_confirmation true
        user.profile.signup_confirmation = 1
        user.save()
        # login(request, user)
        return redirect('home')
    else:
        return render(request, 'activation_invalid.html')

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if request.POST.get("resend-button"):
            userid = request.POST.get("username")
            try:
                user = get_object_or_404(User, username=userid)
            except:
                return render(request, 'signup.html', {'form':form})
            if user.is_active == False:

                subject = 'Please Activate Your Account'
                message = render_to_string('activation_request.html', {
                    'user': user,
                    'domain': get_current_site(request).domain,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': account_activation_token.make_token(user),
                })
                from_email = settings.DJANGO_DEFAULT_FROM_EMAIL
                to = user.email
                msg = EmailMultiAlternatives(subject, message, from_email, [to])
                msg.send(fail_silently=False)
                return redirect('activation_sent')
        ######
        # if user.is_active == 1 and request.POST.get("resend-button"):
        #    return redirect('activation_resend_user_already_exists.html')
        #####
        if form.is_valid() or request.POST.get("resend-button"):
            try:
                user = form.save()
            except Exception as ex:
                return render(request, 'activation_resend_user_already_exists.html')
            user.refresh_from_db()
            user.profile.email = form.cleaned_data.get('email')
            #set user to false until link confirmed
            user.is_active = 0
            user.save()
            subject = 'Please Activate Your Account'
            message = render_to_string('activation_request.html', {
                'user': user,
                'domain': get_current_site(request).domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            from_email = settings.DJANGO_DEFAULT_FROM_EMAIL
            to = user.email
            msg = EmailMultiAlternatives(subject, message, from_email, [to])
            msg.send(fail_silently=False)
            return redirect('activation_sent')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form':form})


def about_view(request):
    return render(request, 'about.html')

def about1_view(request):
    return render(request, 'about1.html')

# Display more detailed information about a station
def station_analysis(request, id=None):
        station = get_object_or_404(Station, id=id)

        #mag_stations = Station.objects.all()
        table = ObservationTable(Observation.objects.filter(station_id=id))
        table.paginate(page=request.GET.get("page", 1), per_page=8)
        return render(request, 'station_analysis.html',
            {'station': station, 'table': table}
                )

#@method_decorator(login_required, name='dispatch')
# Display a list of all registered users
class UserListView(SingleTableView):
    table_class = UserTable
    queryset = User.objects.all()
    template_name = 'user_list.html'
    paginate_by = 8
