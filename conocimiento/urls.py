from django.urls import path
from conocimiento.views import buscar_conocimiento_view

urlpatterns = [
    path('buscar/', buscar_conocimiento_view, name='api_buscar_conocimiento'),
]