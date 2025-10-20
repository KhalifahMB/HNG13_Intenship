from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('profile_app.urls')),
    path('', include('String_Analyser.urls')),
   ]
