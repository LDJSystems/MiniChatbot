"""
tests_chatbot.py — Pruebas unitarias del sistema de memoria conversacional.

Ejecutar con:
    python manage.py test rag.tests_chatbot
"""
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from rest_framework.test import APIRequestFactory

# ---------------------------------------------------------------------------
# Pruebas del módulo views (lógica de clasificación de mensajes)
# ---------------------------------------------------------------------------

class ClasificacionMensajeTests(TestCase):
    """Verifica que los mensajes se clasifican correctamente sin BD."""

    def setUp(self):
        # Importamos aquí para evitar dependencias de app no cargadas
        from rag.views import _es_seguimiento, _detectar_seleccion, _es_catalogo_automatico
        self.es_seguimiento = _es_seguimiento
        self.detectar_seleccion = _detectar_seleccion
        self.es_catalogo = _es_catalogo_automatico

    # -- Seguimiento (Tipo B) --

    def test_seguimiento_cuanto_dura(self):
        self.assertTrue(self.es_seguimiento("¿Cuánto dura?"))

    def test_seguimiento_donde_se_imparte(self):
        self.assertTrue(self.es_seguimiento("¿Dónde se imparte ese curso?"))

    def test_seguimiento_mas_informacion(self):
        self.assertTrue(self.es_seguimiento("Dame más información"))

    def test_no_seguimiento_busqueda_nueva(self):
        self.assertFalse(self.es_seguimiento("Busca cursos de Excel en Burgos"))

    def test_no_seguimiento_vacio(self):
        self.assertFalse(self.es_seguimiento(""))

    # -- Catálogo automático --

    def test_catalogo_automatico(self):
        self.assertTrue(self.es_catalogo("consulta automatica provincia=Burgos"))

    def test_no_catalogo_automatico(self):
        self.assertFalse(self.es_catalogo("Quiero cursos de contabilidad"))

    # -- Selección (Tipo C) --

    def _make_curso(self, pk, titulo, localidad="Burgos"):
        c = MagicMock()
        c.pk = pk
        c.titulo = titulo
        c.localidad = localidad
        return c

    def test_seleccion_por_posicion_primero(self):
        cursos = [self._make_curso(1, "Excel básico"), self._make_curso(2, "Python avanzado")]
        resultado = self.detectar_seleccion("Me interesa el primero", cursos)
        self.assertEqual(resultado.pk, 1)

    def test_seleccion_por_posicion_segundo(self):
        cursos = [self._make_curso(1, "Excel básico"), self._make_curso(2, "Python avanzado")]
        resultado = self.detectar_seleccion("Quiero el segundo", cursos)
        self.assertEqual(resultado.pk, 2)

    def test_seleccion_por_titulo_unico(self):
        cursos = [
            self._make_curso(1, "Administración de redes"),
            self._make_curso(2, "Atención sociosanitaria"),
        ]
        resultado = self.detectar_seleccion("Me interesa el de sociosanitaria", cursos)
        self.assertEqual(resultado.pk, 2)

    def test_seleccion_ambigua_devuelve_none(self):
        cursos = [
            self._make_curso(1, "Atención sociosanitaria Burgos"),
            self._make_curso(2, "Atención sociosanitaria León"),
        ]
        resultado = self.detectar_seleccion("Me interesa el de atención", cursos)
        self.assertIsNone(resultado)

    def test_seleccion_sin_keyword_devuelve_false(self):
        cursos = [self._make_curso(1, "Excel básico")]
        resultado = self.detectar_seleccion("¿Cuánto dura el curso?", cursos)
        self.assertIs(resultado, False)

    def test_seleccion_sin_contexto_devuelve_none(self):
        resultado = self.detectar_seleccion("Me interesa el primero", [])
        self.assertIsNone(resultado)

    def test_seleccion_posicion_fuera_de_rango(self):
        cursos = [self._make_curso(1, "Excel básico")]
        resultado = self.detectar_seleccion("Me interesa el tercero", cursos)
        self.assertIsNone(resultado)


# ---------------------------------------------------------------------------
# Pruebas de caché (aislamiento de sesiones)
# ---------------------------------------------------------------------------

class AislamientoSesionesTests(TestCase):
    """Verifica que sesiones distintas no comparten contexto."""

    def setUp(self):
        from rag.views import _guardar_contexto, _recuperar_contexto
        self.guardar = _guardar_contexto
        self.recuperar = _recuperar_contexto

    def _make_curso_orm(self, pk, titulo):
        c = MagicMock(spec=['pk', 'titulo', 'localidad', 'provincia'])
        c.pk = pk
        c.titulo = titulo
        c.localidad = "Burgos"
        return c

    @patch('rag.views.BaseConocimiento.objects')
    @patch('rag.views.cache')
    def test_sesiones_independientes(self, mock_cache, mock_manager):
        """Dos sesiones diferentes no se mezclan."""
        # Simulamos que la caché devuelve datos distintos según la clave
        almacen = {}

        def fake_set(key, value, timeout=None):
            almacen[key] = value

        def fake_get(key, default=None):
            return almacen.get(key, default)

        mock_cache.set.side_effect = fake_set
        mock_cache.get.side_effect = fake_get

        curso_a = self._make_curso_orm(1, "Excel para administración")
        curso_b = self._make_curso_orm(2, "Python para datos")

        self.guardar("sesion-AAA", [curso_a])
        self.guardar("sesion-BBB", [curso_b])

        datos_a = almacen.get("chat:contexto:sesion-AAA", {})
        datos_b = almacen.get("chat:contexto:sesion-BBB", {})

        self.assertIn(1, datos_a.get("cursos_mostrados", []))
        self.assertNotIn(2, datos_a.get("cursos_mostrados", []))
        self.assertIn(2, datos_b.get("cursos_mostrados", []))
        self.assertNotIn(1, datos_b.get("cursos_mostrados", []))

    @patch('rag.views.cache')
    def test_sesion_sin_uuid_devuelve_vacio(self, mock_cache):
        from rag.views import _recuperar_contexto
        resultado = _recuperar_contexto(None)
        self.assertEqual(resultado["cursos_mostrados"], [])
        self.assertIsNone(resultado["curso_seleccionado"])
        mock_cache.get.assert_not_called()

    @patch('rag.views.cache')
    def test_cache_error_devuelve_vacio(self, mock_cache):
        from rag.views import _recuperar_contexto
        mock_cache.get.side_effect = Exception("Redis no disponible")
        resultado = _recuperar_contexto("sesion-XYZ")
        self.assertEqual(resultado["cursos_mostrados"], [])
        self.assertIsNone(resultado["curso_seleccionado"])


# ---------------------------------------------------------------------------
# Pruebas del generador
# ---------------------------------------------------------------------------

class GeneradorTests(TestCase):
    """Verifica que el generador usa el contexto correcto según el tipo."""

    def _make_curso(self, titulo="Curso de prueba", localidad="Burgos"):
        c = MagicMock()
        c.titulo = titulo
        c.localidad = localidad
        c.provincia = "Burgos"
        c.colectivo = "General"
        c.contenido = "Descripción de prueba."
        c.url_oficial = "https://cefye.es/curso-prueba"
        return c

    @patch('rag.generator.requests.post')
    def test_fallback_activado_cuando_ollama_falla(self, mock_post):
        from rag.generator import generar_respuesta_ia
        mock_post.side_effect = Exception("Ollama no disponible")
        curso = self._make_curso()
        resultado = generar_respuesta_ia("¿Cuánto dura?", [curso], es_seguimiento=True)
        self.assertTrue(resultado["fallback_activado"])
        self.assertIn("Curso de prueba", resultado["texto_respuesta"])

    @patch('rag.generator.requests.post')
    def test_respuesta_correcta_con_ollama(self, mock_post):
        from rag.generator import generar_respuesta_ia
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"response": "El curso dura 3 meses."}

        curso = self._make_curso()
        resultado = generar_respuesta_ia("¿Cuánto dura?", [curso], es_seguimiento=True)
        self.assertFalse(resultado["fallback_activado"])
        self.assertEqual(resultado["texto_respuesta"], "El curso dura 3 meses.")

    @patch('rag.generator.requests.post')
    def test_prompt_seguimiento_curso_unico(self, mock_post):
        """El prompt de seguimiento con un solo curso menciona 'seleccionado'."""
        from rag.generator import generar_respuesta_ia
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = {"response": "Respuesta de prueba."}

        curso = self._make_curso()
        generar_respuesta_ia("¿Es gratuito?", [curso], es_seguimiento=True)

        payload_enviado = mock_post.call_args[1]['json']
        prompt = payload_enviado['prompt']
        self.assertIn("preguntando sobre el curso", prompt)


# ---------------------------------------------------------------------------
# Pruebas del recuperador (sin BD real)
# ---------------------------------------------------------------------------

class RetrieverTests(TestCase):
    """Pruebas de clasificación interna del retriever."""

    def setUp(self):
        from rag.retriever import (
            _limpiar_texto, _detectar_geografia,
            _terminos_tematicos, _terminos_busqueda,
        )
        self.limpiar = _limpiar_texto
        self.detectar_geo = _detectar_geografia
        self.terminos_tematicos = _terminos_tematicos
        self.terminos_busqueda = _terminos_busqueda

    def test_limpiar_texto_elimina_acentos(self):
        self.assertEqual(self.limpiar("Ávila"), "avila")

    def test_detectar_provincia(self):
        prov, loc = self.detectar_geo("cursos en burgos")
        self.assertEqual(prov, "Burgos")
        self.assertIsNone(loc)

    def test_detectar_localidad(self):
        prov, loc = self.detectar_geo("formacion en ponferrada")
        self.assertEqual(prov, "León")
        self.assertEqual(loc, "Ponferrada")

    def test_no_detectar_geografia(self):
        prov, loc = self.detectar_geo("curso de excel")
        self.assertIsNone(prov)
        self.assertIsNone(loc)

    def test_terminos_excluyen_palabras_genericas(self):
        terminos = self.terminos_busqueda("quiero cursos de excel en burgos", "Burgos", None)
        self.assertIn("excel", terminos)
        self.assertNotIn("cursos", terminos)
        self.assertNotIn("quiero", terminos)
        self.assertNotIn("burgos", terminos)