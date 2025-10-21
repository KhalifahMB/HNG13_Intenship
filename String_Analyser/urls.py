from django.urls import path
from .views import StringAnalyzerView, StringDetailView, NaturalLanguageFilterView

urlpatterns = [
    path('strings', StringAnalyzerView.as_view(), name='analyze_string'),
    path('strings/filter-by-natural-language',
         NaturalLanguageFilterView.as_view(), name='nl_filter'),
    path('strings/<str:value>', StringDetailView.as_view(), name='get_string'),

]
