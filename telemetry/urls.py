from django.urls import path

from .views import tendencias_demanda

urlpatterns = [
    path(
        "tendencias/",
        tendencias_demanda,
        name="tendencias_demanda",
    ),
]