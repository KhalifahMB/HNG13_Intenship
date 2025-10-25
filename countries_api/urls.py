from django.urls import path
from . import views

urlpatterns = [
    path('countries/refresh', views.refresh_countries, name='refresh_countries'),
    path('countries/image', views.get_summary_image, name='get_summary_image'),
    path('countries/<str:name>', views.get_country_by_name, name='get_country_by_name'),
    path('countries/<str:name>/delete', views.delete_country, name='delete_country'),
    path('countries', views.get_countries, name='get_countries'),
    path('status', views.get_status, name='get_status'),
]
