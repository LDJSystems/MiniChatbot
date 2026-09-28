from django.urls import path
from .views import lead_create_view

urlpatterns = [
    path('chat/lead/', lead_create_view, name='api-lead-create'),
]