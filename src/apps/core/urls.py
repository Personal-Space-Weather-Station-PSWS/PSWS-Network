from django.urls import path
from .views import under_construction

urlpatterns = [
    path("under_construction/", under_construction, name="under_construction"),
]