# rag/urls.py
from django.urls import path
from rag.views import chat_ask_view

urlpatterns = [
    path('ask/', chat_ask_view, name='api_rag_ask'),
]