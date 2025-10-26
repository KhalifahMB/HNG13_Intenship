from django.urls import path
from . import views

urlpatterns = [
    path('countries/refresh', views.refresh_countries, name='refresh_countries'),
    path('countries/image', views.get_summary_image, name='get_summary_image'),
    path('countries/<str:name>', views.delete_country, name='country_detail'),
    path('countries', views.get_countries, name='get_countries'),
    path('status', views.get_status, name='get_status'),
]
