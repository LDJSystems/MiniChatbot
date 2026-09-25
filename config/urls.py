from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/conocimiento/', include('conocimiento.urls')),
    path('api/chat/', include('rag.urls')),
]