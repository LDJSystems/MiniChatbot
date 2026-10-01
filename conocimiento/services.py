import re
import operator
from functools import reduce
from django.contrib.postgres.search import SearchQuery, SearchRank
from conocimiento.models import BaseConocimiento

class ChatbotKnowledgeService:
    @staticmethod
    def recuperar_contexto(pregunta: str, limite: int = 3) -> str:
        terminos = [w for w in re.findall(r'\w+', pregunta) if len(w) > 2]
        
        if not terminos:
            return "No se encontró información relevante en la base de conocimiento."
            
        query = reduce(operator.or_, [SearchQuery(t, config='spanish') for t in terminos])
        
        resultados = BaseConocimiento.objects.filter(
            vector_busqueda=query,
            activo=True
        ).annotate(
            rank=SearchRank('vector_busqueda', query)
        ).order_by('-rank')[:limite]
        
        if not resultados.exists():
            return "No se encontró información relevante en la base de conocimiento."
            
        contexto_partes = []
        for r in resultados:
            contexto_partes.append(
                f"- Título: {r.titulo}\n"
                f"  Contenido: {r.contenido}\n"
                f"  Provincia: {r.provincia} | Campo: {r.campo_estudio} | Colectivo: {r.colectivo}\n"
                f"  URL Oficial: {r.url_oficial or 'N/D'}"
            )
            
        return "\n\n".join(contexto_partes)