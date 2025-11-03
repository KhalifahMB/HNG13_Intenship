# agent/urls.py
from django.urls import path
from .views import A2AAgentView

urlpatterns = [
    path("edusimplify", A2AAgentView.as_view(), name="edusimplify-a2a"),
]
