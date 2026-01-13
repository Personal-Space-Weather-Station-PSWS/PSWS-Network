from django.shortcuts import render

def under_construction(request, id=None):
    return render(request, "under_construction.html")