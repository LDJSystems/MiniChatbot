from django.urls import path
from conocimiento.views import buscar_conocimiento_view, chatbot_query_view

urlpatterns = [
    path('buscar/', buscar_conocimiento_view, name='api_buscar_conocimiento'),
    path('chat/', chatbot_query_view, name='api_chatbot_query'),
]