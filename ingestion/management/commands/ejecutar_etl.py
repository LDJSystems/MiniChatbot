# conocimiento/management/commands/ejecutar_etl.py
import re
import hashlib
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.db import DatabaseError, transaction
from conocimiento.models import StagingCursos, BaseConocimiento
from conocimiento.services import promover_staging

logger = logging.getLogger(__name__)

PROVINCIAS_CYL = {
    "Ávila", "Burgos", "León", "Palencia",
    "Salamanca", "Segovia", "Soria", "Valladolid", "Zamora"
}
# Niveles de localidad para la provincia de León:
#   1) LOCALIDAD_CAPITAL_LEON: consta que el curso es en la ciudad de León.
#   2) Un municipio concreto de la provincia (Ponferrada, Astorga, ...).
#   3) LOCALIDAD_LEON_SIN_ESPECIFICAR: consta la provincia, pero no la localidad.
# Antes el caso 3 se guardaba como "León (Capital)", mezclando ambos niveles.
LOCALIDAD_CAPITAL_LEON = "León (Capital)"
LOCALIDAD_LEON_SIN_ESPECIFICAR = "León (provincia)"

MAPA_LOCALIDADES_CYL = {
    "Ávila": ["Ávila", "Arenas de San Pedro", "Arévalo", "Candeleda", "El Barco de Ávila", "Las Navas del Marqués"],
    "Burgos": ["Burgos", "Miranda de Ebro", "Aranda de Duero", "Briviesca", "Medina de Pomar", "Villarcayo de Merindad de Castilla La Vieja"],
    "León": [
        LOCALIDAD_CAPITAL_LEON, "Ponferrada", "San Andrés del Rabanedo", "Villaquilambre",
        "Astorga", "La Bañeza", "Bembibre", "Valencia de Don Juan",
        "Villablino", "Sahagún", "Cacabelos", "Villafranca del Bierzo",
        "La Robla", "Cistierna", "Camponaraya", "Fabero", "Santa María del Páramo",
    ],
    "Palencia": ["Palencia", "Aguilar de Campoo", "Guardo", "Venta de Baños", "Villamuriel de Cerrato", "Herrera de Pisuerga"],
    "Salamanca": ["Salamanca", "Béjar", "Ciudad Rodrigo", "Santa Marta de Tormes", "Carbajosa de la Sagrada", "Peñaranda de Bracamonte", "Guijuelo"],
    "Segovia": ["Segovia", "Cuéllar", "El Espinar", "Real Sitio de San Ildefonso", "Palazuelos de Eresma", "Nava de la Asunción"],
    "Soria": ["Soria", "Almazán", "El Burgo de Osma-Ciudad de Osma", "Golmayo", "San Esteban de Gormaz", "Ágreda"],
    "Valladolid": ["Valladolid", "Laguna de Duero", "Medina del Campo", "Arroyo de la Encomienda", "Tordesillas", "Cistérniga", "Zaratán", "Simancas"],
    "Zamora": ["Zamora", "Benavente", "Toro", "Morales del Vino", "Puebla de Sanabria", "Villaralbo"]
}
# Expresiones (ya sin tildes ni mayúsculas) que indican la CIUDAD de León y no
# la provincia. Un "León" a secas se interpreta como provincia.
ALIAS_CAPITAL_LEON = [
    r'leon\s*\(\s*capital\s*\)',
    r'leon\s+capital',
    r'ciudad\s+de\s+leon',
    r'municipio\s+de\s+leon',
    r'capital\s+de\s+leon',
    r'capital\s+leonesa',
]
# Cada patrón lleva un indicador: True si lo capturado se refiere a una
# provincia (un "León" ahí NO se asume ciudad), False si se refiere a un
# lugar de impartición (un "León" ahí se asume ciudad).
PATRONES_UBICACION = [
    (r'[Ii]mpartido\s+en\s+([^\n\.\<]{3,80})', False),
    (r'[Pp]rovincia\s+de\s+([^\n\.\<]{3,80})', True),
    (r'[Pp]rovincias\s+de\s+([^\n\.\<]{3,80})', True),
    (r'[Ss]ede[:\s]+([^\n\.\<]{3,80})', False),
    (r'[Ll]ugar[:\s]+([^\n\.\<]{3,80})', False),
]

# FIX #5: Define aquí el umbral mínimo de cursos válidos para ejecutar
# la desactivación de registros. Si se obtienen menos cursos que este
# valor, se asume un fallo parcial del scraping y NO se desactiva nada.
MIN_CURSOS_PARA_DESACTIVAR = 50   # <-- ajusta según tu volumen esperado


# --- Utilidades -----------------------------------------------------------

def _limpiar_texto(texto: str) -> str:
    if not texto:
        return ""
    return (texto.lower()
            .replace('á', 'a').replace('é', 'e').replace('í', 'i')
            .replace('ó', 'o').replace('ú', 'u').replace('ñ', 'n'))

_RE_CASTILLA_Y_LEON = re.compile(r'castilla\s*(?:y|-|/)?\s*leon')

def _preparar(texto: str) -> str:
    """
    Normaliza el texto y elimina "Castilla y León" (y variantes), para que
    ese "León" de la comunidad autónoma no se confunda con la provincia.
    """
    return _RE_CASTILLA_Y_LEON.sub(' ', _limpiar_texto(texto))

def _compilar(patron: str):
    # Límites de palabra con lookarounds (\b falla tras un paréntesis).
    return re.compile(r'(?<![a-z0-9])(?:' + patron + r')(?![a-z0-9])')

def _construir_indices():
    """Precompila las expresiones de localidades y provincias una sola vez."""
    localidades, provincias = [], []
    for prov, locs in MAPA_LOCALIDADES_CYL.items():
        for loc in locs:
            if loc == LOCALIDAD_CAPITAL_LEON:
                patron = "|".join(ALIAS_CAPITAL_LEON)
                clave = max(len(a) for a in ALIAS_CAPITAL_LEON)
            else:
                norm = _limpiar_texto(loc)
                patron = re.escape(norm)
                clave = len(norm)
            localidades.append((prov, loc, _compilar(patron), clave))
    for prov in sorted(PROVINCIAS_CYL):
        provincias.append((prov, _compilar(re.escape(_limpiar_texto(prov)))))
    return localidades, provincias

_INDICE_LOCALIDADES, _INDICE_PROVINCIAS = _construir_indices()

def _buscar_en_texto(texto_prep: str, solo_localidades_de: str = None):
    """
    Busca en un texto ya preparado (_preparar). Devuelve (provincia, localidad)
    o (None, None).

    - Primero se buscan localidades y después provincias.
    - Entre varias coincidencias gana la que aparece antes en el texto; a igual
      posición, la más larga ("El Barco de Ávila" antes que "Ávila").
    - Si se indica `solo_localidades_de`, solo se consideran las localidades de
      esa provincia y no se busca la provincia en sí.
    """
    mejor = None
    for prov, loc, rx, clave in _INDICE_LOCALIDADES:
        if solo_localidades_de and prov != solo_localidades_de:
            continue
        m = rx.search(texto_prep)
        if m:
            cand = (m.start(), -clave, prov, loc)
            if mejor is None or cand < mejor:
                mejor = cand
    if mejor:
        return mejor[2], mejor[3]

    if solo_localidades_de:
        return None, None

    for prov, rx in _INDICE_PROVINCIAS:
        m = rx.search(texto_prep)
        if m:
            cand = (m.start(), 0, prov, "")
            if mejor is None or cand < mejor:
                mejor = cand
    if mejor:
        return mejor[2], mejor[3]
    return None, None

def _buscar_en_fragmento(fragmento: str, es_patron_provincial: bool = False):
    """
    Busca provincia/localidad en el fragmento capturado por un patrón explícito.
    Si el fragmento solo dice "León" y el patrón es de lugar de impartición
    ("Impartido en León", "Sede: León"), se asume la ciudad de León.
    """
    frag = _preparar(fragmento)
    prov, loc = _buscar_en_texto(frag)
    if (prov == "León" and not loc
            and not es_patron_provincial
            and 'provincia' not in frag):
        loc = LOCALIDAD_CAPITAL_LEON
    return prov, loc


def _normalizar_localidad_leon(provincia: str, localidad: str, texto_cuerpo: str) -> str:
    """
    Resuelve la localidad final para la provincia de León.

    - Si la provincia no es León, devuelve la localidad tal cual.
    - Si ya se detectó una localidad (capital o municipio), se respeta.
    - Si no, se buscan municipios de la provincia en el cuerpo de la página
      (sin menús ni cabecera).
    - Si sigue sin haber nada, se devuelve LOCALIDAD_LEON_SIN_ESPECIFICAR en
      lugar de asumir la capital.
    """
    if provincia != "León":
        return localidad
    if localidad:
        return localidad

    _, loc = _buscar_en_texto(_preparar(texto_cuerpo), solo_localidades_de="León")
    return loc or LOCALIDAD_LEON_SIN_ESPECIFICAR


def _extraer_provincia_localidad(soup: BeautifulSoup):
    """
    Detecta (provincia, localidad) de un curso.

    Fase 1: patrones explícitos ("Impartido en", "Provincia de", "Sede", ...).
    Fase 2: búsqueda libre en el cuerpo (nav y header eliminados).
    Después, para León, se afina la localidad con _normalizar_localidad_leon.
    """
    for tag in soup.find_all(['nav', 'header']):
        tag.decompose()

    texto_cuerpo = soup.get_text(separator="\n")
    prov, loc = "General", ""

    # Fase 1: patrones de ubicación explícitos
    for patron, es_provincial in PATRONES_UBICACION:
        for match in re.finditer(patron, texto_cuerpo):
            p, l = _buscar_en_fragmento(match.group(1).strip(), es_provincial)
            if p:
                prov, loc = p, l
                break
        if prov != "General":
            break

    # Fase 2: búsqueda libre si los patrones no encontraron nada
    if prov == "General":
        p, l = _buscar_en_texto(_preparar(texto_cuerpo))
        if p:
            prov, loc = p, l

    loc = _normalizar_localidad_leon(prov, loc, texto_cuerpo)
    return prov, loc


def _extraer_colectivo(texto_limpio: str) -> str:
    if any(k in texto_limpio for k in ["desemplead", "trabajador", "demandante"]):
        return "Personas desempleadas y trabajadoras"
    if "discapacidad" in texto_limpio:
        return "Personas con discapacidad"
    if "mayores" in texto_limpio or "jubilad" in texto_limpio:
        return "Mayores"
    return "General"

def _extraer_horas(soup: BeautifulSoup) -> str:
    """
    FIX #8: opera sobre el soup en lugar de texto plano, capturando horas
    aunque estén dentro de <strong>, <b>, <span> u otros tags inline.
    """
    texto = soup.get_text(separator=" ")
    match = re.search(r'(\d+)\s*horas?', texto, re.IGNORECASE)
    return f"{match.group(1)} horas" if match else ""


def _extraer_modalidad(texto_limpio: str) -> str:
    if "teleformacion" in texto_limpio or "online" in texto_limpio:
        return "Teleformación"
    if "presencial" in texto_limpio:
        return "Presencial"
    return "General"


def _normalizar_url(url: str) -> str:
    """Normaliza URLs garantizando barra final, para evitar duplicados."""
    return url.rstrip('/') + '/'


# --- Comando Django -------------------------------------------------------

class Command(BaseCommand):
    help = "Pipeline ETL: extrae cursos de cefye.com y los carga en BaseConocimiento."

    def handle(self, *args, **options):
        self.stdout.write("Iniciando proceso ETL web...")

        datos_crudos = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        session = requests.Session()
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retries))

        # --- Fase 1: obtener índice de cursos ---
        URL_BASE_CURSOS = _normalizar_url("https://www.cefye.com/cursos/")

        try:
            response = session.get(URL_BASE_CURSOS, headers=headers, timeout=15)
            response.raise_for_status()
            soup_index = BeautifulSoup(response.text, 'html.parser')

            enlaces_cursos = set()
            for a in soup_index.find_all('a', href=True):
                href = a['href']
                if re.search(r'/cursos/[^/]+/?$', href):
                    full_url = _normalizar_url(
                        href if href.startswith('http') else f"https://www.cefye.com{href}"
                    )
                    # FIX #3: comparamos URLs normalizadas para excluir la página índice
                    if full_url != URL_BASE_CURSOS:
                        enlaces_cursos.add(full_url)

            self.stdout.write(f"  Enlaces de cursos encontrados: {len(enlaces_cursos)}")

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error al obtener el índice de cursos: {e}"))
            return

        # --- Fase 2: scraping de cada curso ---
        descartados = 0
        urls_404: set[str] = set()

        for url_curso in enlaces_cursos:
            try:
                res_detalle = session.get(url_curso, headers=headers, timeout=15)
                if res_detalle.status_code == 404:
                    logger.warning(f"HTTP 404 en {url_curso} — se marcará como inactiva en BD")
                    urls_404.add(url_curso)
                    continue
                if res_detalle.status_code != 200:
                    logger.warning(f"HTTP {res_detalle.status_code} en {url_curso}")
                    continue

                soup_det = BeautifulSoup(res_detalle.text, 'html.parser')

                h1 = soup_det.find('h1')
                titulo = h1.get_text(strip=True) if h1 else "Curso CEFYE"

                # FIX #8: extraemos horas ANTES de mutar el soup
                horas = _extraer_horas(soup_det)

                # _extraer_provincia_localidad elimina nav/header del soup y distingue
                # León provincia / León capital / municipios de la provincia
                provincia, localidad_encontrada = _extraer_provincia_localidad(soup_det)

                if provincia not in PROVINCIAS_CYL:
                    logger.info(f"Descartado (fuera de CyL): {url_curso} → provincia='{provincia}'")
                    descartados += 1
                    continue

                # El soup ya está mutado (sin nav/header) tras _extraer_provincia_localidad
                for tag in soup_det.find_all(['footer']):
                    tag.decompose()

                parrafos = [
                    p.get_text(strip=True)
                    for p in soup_det.find_all(['p', 'li', 'span'])
                    if p.get_text(strip=True)
                ]
                contenido_completo = " ".join(parrafos)
                texto_limpio = _limpiar_texto(contenido_completo)

                colectivo = _extraer_colectivo(texto_limpio)
                modalidad = _extraer_modalidad(texto_limpio)

                contenido_enriquecido = (
                    f"{contenido_completo} "
                    f"Provincia: {provincia}. "
                    f"Localidad: {localidad_encontrada}. "
                    f"Modalidad: {modalidad}. "
                    f"Duración: {horas}. "
                    f"Colectivo: {colectivo}."
                )

                datos_crudos.append({
                    "titulo": titulo,
                    "contenido": contenido_enriquecido,
                    "provincia": provincia,
                    "localidad": localidad_encontrada,
                    "campo_estudio": "Formación Profesional y Empleo",
                    "colectivo": colectivo,
                    "url": url_curso
                })

            except Exception as ex:
                logger.error(f"Error procesando {url_curso}: {ex}")

        self.stdout.write(
            f"  Cursos válidos extraídos: {len(datos_crudos)} | "
            f"Descartados (fuera de CyL): {descartados} | "
            f"URLs con 404: {len(urls_404)}"
        )

        # --- Fase 3: carga en staging ---
        staging_ids = []
        errores_staging = 0

        for item in datos_crudos:
            try:
                hash_input = f"{item['url']}|{item['titulo']}"
                hash_val = hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

                with transaction.atomic():
                    obj, _ = StagingCursos.objects.update_or_create(
                        hash_contenido=hash_val,
                        defaults={
                            'titulo_raw':        item['titulo'],
                            'contenido_raw':     item['contenido'],
                            'provincia_raw':     item['provincia'],
                            'localidad':         item['localidad'],
                            'campo_estudio_raw': item['campo_estudio'],
                            'colectivo_raw':     item['colectivo'],
                            'url_origen':        item['url'],
                            'estado':            'pendiente',
                        }
                    )
                    staging_ids.append(obj.pk)

            except DatabaseError as e:
                logger.error(f"Error de BD guardando staging {item.get('url')}: {e}")
                errores_staging += 1

        self.stdout.write(
            f"  Staging: {len(staging_ids)} registros listos, "
            f"{errores_staging} errores."
        )

        # --- Fase 3b: promover staging → BaseConocimiento ---
        qs_a_promover = StagingCursos.objects.filter(pk__in=staging_ids, estado='pendiente')
        resultado = promover_staging(queryset=qs_a_promover)

        if resultado['errores']:
            self.stdout.write(
                self.style.WARNING(
                    f"  Errores en promoción: {resultado['ids_error']}"
                )
            )

        # --- Fase 4a: desactivar cursos que devolvieron 404 en esta ejecución ---
        desactivados_404 = 0
        if urls_404:
            desactivados_404 = BaseConocimiento.objects.filter(
                url_oficial__in=urls_404,
                activo=True
            ).update(activo=False)
            if desactivados_404:
                self.stdout.write(
                    self.style.WARNING(
                        f"  {desactivados_404} registro(s) desactivado(s) por 404: "
                        + ", ".join(urls_404)
                    )
                )

        # --- Fase 4b: desactivar cursos que ya no aparecen en la web ---
        # FIX #5: solo desactivamos si el scraping ha obtenido un mínimo razonable
        # de cursos; si hay menos, asumimos fallo parcial y no tocamos nada.
        desactivados = 0
        if len(datos_crudos) >= MIN_CURSOS_PARA_DESACTIVAR:
            urls_activas = {item['url'] for item in datos_crudos}
            desactivados = BaseConocimiento.objects.filter(activo=True).exclude(
                url_oficial__in=urls_activas
            ).update(activo=False)
        else:
            logger.warning(
                f"Scraping incompleto ({len(datos_crudos)} cursos < umbral {MIN_CURSOS_PARA_DESACTIVAR}). "
                "Se omite la desactivación de registros para evitar bajas masivas incorrectas."
            )

        self.stdout.write(self.style.SUCCESS(
            f"ETL completado: {resultado['procesados']} promovidos a producción, "
            f"{desactivados + desactivados_404} desactivados "
            f"({desactivados_404} por 404, {desactivados} por ausencia), "
            f"{errores_staging + resultado['errores']} errores totales."
        ))