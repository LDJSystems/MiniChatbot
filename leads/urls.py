from django.urls import path

from .views import LeadCreateView


urlpatterns = [
    path(
        "lead/",
        LeadCreateView.as_view(),
        name="lead-create",
    ),
]