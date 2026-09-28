from django.urls import path
from .views import lead_create_view

urlpatterns = [
    path('lead/', lead_create_view, name='api-lead-create'),
]