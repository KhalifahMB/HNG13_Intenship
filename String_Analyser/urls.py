from django.urls import path
from .views import StringAnalyzerView, StringDetailView, StringListView, StringDeleteView, NaturalLanguageFilterView

urlpatterns = [
    path('string', StringAnalyzerView.as_view(), name='analyze_string'),
    path('string/<str:value>', StringDetailView.as_view(), name='get_string'),
    path('string/<str:value>/delete',
         StringDeleteView.as_view(), name='delete_string'),
    path('strings', StringListView.as_view(), name='list_strings'),
    path('strings/filter-by-natural-language', NaturalLanguageFilterView.as_view(), name='nl_filter'),
]
