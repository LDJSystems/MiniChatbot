from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/conocimiento/', include('conocimiento.urls')),
    path('api/chat/', include('rag.urls')),
<<<<<<< HEAD
    path('api/chat/', include('leads.urls')),
=======
    path('api/', include('operaciones.urls')),
>>>>>>> 5025bb1 (feat: añadir modelos Provincia y Localidad, migraciones de Castilla y León y validación en LeadSerializer)
]