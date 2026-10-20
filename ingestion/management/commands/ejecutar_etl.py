import re
import hashlib
import logging
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from django.core.management.base import BaseCommand
from django.db import DatabaseError, transaction

from conocimiento.models import StagingCursos, BaseConocimiento
from conocimiento.services import promover_staging


logger = logging.getLogger(__name__)

URL_BASE_CURSOS = "https://www.cefye.com/cursos/"
DOMINIO_CEFYE = "www.cefye.com"

MIN_CURSOS_PARA_DESACTIVAR = 20

PROVINCIAS_CYL = {
    "Ávila", "Burgos", "León", "Palencia",
    "Salamanca", "Segovia", "Soria", "Valladolid", "Zamora"
}

LOCALIDAD_CAPITAL_LEON = "León (Capital)"
LOCALIDAD_LEON_SIN_ESPECIFICAR = "León (provincia)"

MAPA_LOCALIDADES_CYL = {
    "Ávila": [
        "Ávila", "Arenas de San Pedro", "Arévalo", "Candeleda",
        "El Barco de Ávila", "Las Navas del Marqués"
    ],
    "Burgos": [
        "Burgos", "Miranda de Ebro", "Aranda de Duero",
        "Briviesca", "Medina de Pomar",
        "Villarcayo de Merindad de Castilla La Vieja"
    ],
    "León": [
        LOCALIDAD_CAPITAL_LEON, "Ponferrada", "San Andrés del Rabanedo",
        "Villaquilambre", "Astorga", "La Bañeza", "Bembibre",
        "Valencia de Don Juan", "Villablino", "Sahagún", "Cacabelos",
        "Villafranca del Bierzo", "La Robla", "Cistierna",
        "Camponaraya", "Fabero", "Santa María del Páramo"
    ],
    "Palencia": [
        "Palencia", "Aguilar de Campoo", "Guardo", "Venta de Baños",
        "Villamuriel de Cerrato", "Herrera de Pisuerga"
    ],
    "Salamanca": [
        "Salamanca", "Béjar", "Ciudad Rodrigo", "Santa Marta de Tormes",
        "Carbajosa de la Sagrada", "Peñaranda de Bracamonte", "Guijuelo"
    ],
    "Segovia": [
        "Segovia", "Cuéllar", "El Espinar", "Real Sitio de San Ildefonso",
        "Palazuelos de Eresma", "Nava de la Asunción"
    ],
    "Soria": [
        "Soria", "Almazán", "El Burgo de Osma-Ciudad de Osma",
        "Golmayo", "San Esteban de Gormaz", "Ágreda"
    ],
    "Valladolid": [
        "Valladolid", "Laguna de Duero", "Medina del Campo",
        "Arroyo de la Encomienda", "Tordesillas", "Cistérniga",
        "Zaratán", "Simancas"
    ],
    "Zamora": [
        "Zamora", "Benavente", "Toro", "Morales del Vino",
        "Puebla de Sanabria", "Villaralbo"
    ]
}

ALIAS_CAPITAL_LEON = [
    r"leon\s*\(\s*capital\s*\)",
    r"leon\s+capital",
    r"ciudad\s+de\s+leon",
    r"municipio\s+de\s+leon",
    r"capital\s+de\s+leon",
    r"capital\s+leonesa",
]

PATRONES_UBICACION = [
    (r"[Ii]mpartido\s+en\s+([^\n.<]{3,80})", False),
    (r"[Pp]rovincia\s+de\s+([^\n.<]{3,80})", True),
    (r"[Pp]rovincias\s+de\s+([^\n.<]{3,80})", True),
    (r"[Ss]ede[:\s]+([^\n.<]{3,80})", False),
    (r"[Ll]ugar[:\s]+([^\n.<]{3,80})", False),
]


# ---------------------------------------------------------------------
# Utilidades de texto y localización
# ---------------------------------------------------------------------

def _limpiar_texto(texto: str) -> str:
    """Normaliza acentos y minúsculas para comparar texto."""
    if not texto:
        return ""

    texto = texto.lower()

    traducciones = str.maketrans({
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ü": "u",
        "ñ": "n",
    })

    return texto.translate(traducciones)


_RE_CASTILLA_Y_LEON = re.compile(
    r"castilla\s*(?:y|-|/)?\s*leon"
)


def _preparar(texto: str) -> str:
    return _RE_CASTILLA_Y_LEON.sub(" ", _limpiar_texto(texto))


def _compilar(patron: str):
    return re.compile(
        r"(?<![a-z0-9])(?:" + patron + r")(?![a-z0-9])"
    )


def _construir_indices():
    localidades = []
    provincias = []

    for provincia, localidades_provincia in MAPA_LOCALIDADES_CYL.items():
        for localidad in localidades_provincia:
            if localidad == LOCALIDAD_CAPITAL_LEON:
                patron = "|".join(ALIAS_CAPITAL_LEON)
                clave = max(len(alias) for alias in ALIAS_CAPITAL_LEON)
            else:
                norm = _limpiar_texto(localidad)
                patron = re.escape(norm)
                clave = len(norm)

            localidades.append(
                (provincia, localidad, _compilar(patron), clave)
            )

    for provincia in sorted(PROVINCIAS_CYL):
        provincias.append(
            (
                provincia,
                _compilar(re.escape(_limpiar_texto(provincia)))
            )
        )

    return localidades, provincias


_INDICE_LOCALIDADES, _INDICE_PROVINCIAS = _construir_indices()


def _buscar_en_texto(
    texto_prep: str,
    solo_localidades_de: str = None
):
    mejor = None

    for provincia, localidad, rx, clave in _INDICE_LOCALIDADES:
        if solo_localidades_de and provincia != solo_localidades_de:
            continue

        match = rx.search(texto_prep)

        if match:
            candidato = (
                match.start(),
                -clave,
                provincia,
                localidad
            )

            if mejor is None or candidato < mejor:
                mejor = candidato

    if mejor:
        return mejor[2], mejor[3]

    if solo_localidades_de:
        return None, None

    for provincia, rx in _INDICE_PROVINCIAS:
        match = rx.search(texto_prep)

        if match:
            candidato = (match.start(), 0, provincia, "")

            if mejor is None or candidato < mejor:
                mejor = candidato

    if mejor:
        return mejor[2], mejor[3]

    return None, None


def _buscar_en_fragmento(
    fragmento: str,
    es_patron_provincial: bool = False
):
    fragmento_preparado = _preparar(fragmento)
    provincia, localidad = _buscar_en_texto(fragmento_preparado)

    if (
        provincia == "León"
        and not localidad
        and not es_patron_provincial
        and "provincia" not in fragmento_preparado
    ):
        localidad = LOCALIDAD_CAPITAL_LEON

    return provincia, localidad


def _normalizar_localidad_leon(
    provincia: str,
    localidad: str,
    texto_cuerpo: str
) -> str:
    if provincia != "León":
        return localidad

    if localidad:
        return localidad

    _, localidad_encontrada = _buscar_en_texto(
        _preparar(texto_cuerpo),
        solo_localidades_de="León"
    )

    return (
        localidad_encontrada
        or LOCALIDAD_LEON_SIN_ESPECIFICAR
    )


def _extraer_provincia_localidad(soup: BeautifulSoup):
    texto_cuerpo = soup.get_text(separator="\n", strip=True)
    provincia, localidad = "General", ""

    for patron, es_provincial in PATRONES_UBICACION:
        for match in re.finditer(patron, texto_cuerpo):
            p, l = _buscar_en_fragmento(
                match.group(1).strip(),
                es_provincial
            )

            if p:
                provincia, localidad = p, l
                break

        if provincia != "General":
            break

    if provincia == "General":
        p, l = _buscar_en_texto(_preparar(texto_cuerpo))

        if p:
            provincia, localidad = p, l

    localidad = _normalizar_localidad_leon(
        provincia,
        localidad,
        texto_cuerpo
    )

    return provincia, localidad


# ---------------------------------------------------------------------
# Extracción de títulos, duración y datos del curso
# ---------------------------------------------------------------------

def _normalizar_titulo_comparacion(texto: str) -> str:
    texto = re.sub(r"\s+", " ", texto or "").strip().casefold()
    texto = re.sub(r"\s*[-–—:]\s*", "-", texto)
    return texto


def _limpiar_titulo_curso(texto: str) -> str:
    """Elimina sufijos SEO y texto que no forma parte del título."""
    if not texto:
        return ""

    texto = re.sub(r"\s+", " ", texto).strip()

    # Elimina sufijos de marca o SEO.
    texto = re.sub(
        r"\s*[-|–—]\s*CEFYE(?:\s*[-|–—]\s*Centro Empresarial "
        r"de Formación y Empleo)?\s*$",
        "",
        texto,
        flags=re.IGNORECASE
    )

    texto = re.sub(
        r"\s*[-|–—]\s*Centro Empresarial de Formación y Empleo\s*$",
        "",
        texto,
        flags=re.IGNORECASE
    )

    return texto.strip(" -–—|:")




def _extraer_titulo_curso(
    soup: BeautifulSoup,
    url: str
) -> str:
    """
    Prioriza los encabezados que identifican el curso por su código.
    Después utiliza h1, metadatos SEO y, como último recurso, la URL.
    """
    genericos = {
        "curso cefye",
        "cursos cefye",
        "cefye",
    }

    titulos_genericos = {
        "presencial",
        "teleformacion",
        "online",
        "duracion",
        "modalidad",
    }

    # El código debe empezar por letras y puede contener números.
    patron_codigo = re.compile(
        r"^\s*([A-Z]{2,}[A-Z0-9]*)\s*[-–—:]\s*(.+?)\s*$",
        re.IGNORECASE,
    )

    # Priorizar encabezados que identifiquen realmente el curso.
    for etiqueta in ("h2", "h1", "h3", "h4"):
        for encabezado in soup.find_all(etiqueta):
            linea = encabezado.get_text(" ", strip=True)
            linea = _limpiar_titulo_curso(linea)

            if not linea:
                continue

            # Corregir códigos separados accidentalmente por una letra.
            # Ejemplo: "A DGG020PO-Excel avanzado"
            # se convierte en "ADGG020PO-Excel avanzado".
            linea = re.sub(
                r"^\s*([A-Z])\s+([A-Z]{2,}[A-Z0-9]*\s*[-–—:])",
                r"\1\2",
                linea,
                flags=re.IGNORECASE,
            )

            # Ignorar encabezados que solo describen la modalidad.
            if _limpiar_texto(linea).strip(" :-").casefold() in titulos_genericos:
                continue

            # Buscar el código en el encabezado actual.
            match = patron_codigo.match(linea)

            if match:
                codigo = match.group(1).upper()
                nombre = match.group(2).strip(" -–—:.")

                # Quitar textos promocionales o información adicional.
                nombre = re.split(
                    r"\b(?:impartido por|formación 100%\s*gratuita|"
                    r"modalidad|duración)\b",
                    nombre,
                    maxsplit=1,
                    flags=re.IGNORECASE,
                )[0].strip(" -–—:.")

                if not nombre:
                    continue

                if (
                    _limpiar_texto(nombre)
                    .strip(" :-")
                    .casefold() in titulos_genericos
                ):
                    continue

                return f"{codigo} - {nombre}"

    # Fallback: h1.
    h1 = soup.find("h1")
    titulo_h1 = h1.get_text(" ", strip=True) if h1 else ""
    titulo_h1 = _limpiar_titulo_curso(titulo_h1)

    if titulo_h1:
        titulo_h1 = re.sub(
            r"^\s*([A-Z])\s+([A-Z]{2,}[A-Z0-9]*\s*[-–—:])",
            r"\1\2",
            titulo_h1,
            flags=re.IGNORECASE,
        )

    if (
        titulo_h1
        and titulo_h1.casefold() not in genericos
        and _limpiar_texto(titulo_h1).strip(" :-").casefold()
        not in titulos_genericos
    ):
        return titulo_h1

    # Fallback: metadatos de la página.
    candidatos = []

    if soup.title:
        candidatos.append(soup.title.get_text(" ", strip=True))

    for atributo in ("og:title", "twitter:title"):
        meta = soup.find("meta", attrs={"property": atributo})

        if not meta:
            meta = soup.find("meta", attrs={"name": atributo})

        if meta and meta.get("content"):
            candidatos.append(meta["content"].strip())

    for candidato in candidatos:
        candidato = _limpiar_titulo_curso(candidato)

        if not candidato:
            continue

        candidato = re.sub(
            r"^\s*([A-Z])\s+([A-Z]{2,}[A-Z0-9]*\s*[-–—:])",
            r"\1\2",
            candidato,
            flags=re.IGNORECASE,
        )

        if candidato.casefold() in genericos:
            continue

        if (
            _limpiar_texto(candidato).strip(" :-").casefold()
            in titulos_genericos
        ):
            continue

        return candidato

    # Último recurso: obtener el título del slug de la URL.
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    slug = re.sub(
        r"\.(?:html?|php)$",
        "",
        slug,
        flags=re.IGNORECASE,
    )
    slug = re.sub(r"[-_]+", " ", slug).strip()

    return slug[:1].upper() + slug[1:] if slug else ""




def _extraer_codigo_titulo(titulo: str) -> str:
    """Devuelve el código del curso si aparece al principio del título."""
    match = re.match(
        r"^\s*([A-Z]{2,}[A-Z0-9]*)\s*[-–—:]",
        titulo or "",
        re.IGNORECASE
    )
    return match.group(1).upper() if match else ""


def _buscar_bloque_curso(
    soup: BeautifulSoup,
    titulo: str
):
    """
    Busca bloques de duración vinculados al curso.

    Primero utiliza encabezados con el mismo código o título.
    Después examina bloques de Elementor que contengan una duración.
    No considera fiable un contenedor que mezcle varias duraciones.
    """
    if not titulo:
        return None

    titulo_objetivo = _normalizar_titulo_comparacion(titulo)
    codigo = _extraer_codigo_titulo(titulo)

    encabezados = soup.find_all(["h1", "h2", "h3", "h4"])
    encabezado_objetivo = None

    for encabezado in encabezados:
        texto = encabezado.get_text(" ", strip=True)
        texto_normalizado = _normalizar_titulo_comparacion(texto)

        mismo_titulo = texto_normalizado == titulo_objetivo

        mismo_codigo = (
            bool(codigo)
            and _extraer_codigo_titulo(texto) == codigo
        )

        if mismo_titulo or mismo_codigo:
            encabezado_objetivo = encabezado
            break

    # Método 1: buscar un contenedor pequeño alrededor del encabezado.
    if encabezado_objetivo:
        for padre in encabezado_objetivo.parents:
            if not getattr(padre, "get_text", None):
                continue

            if getattr(padre, "name", None) in ("html", "body"):
                continue

            texto = re.sub(
                r"\s+",
                " ",
                padre.get_text(" ", strip=True)
            ).strip()

            if not texto or len(texto) > 3500:
                continue

            duraciones = re.findall(
                r"\b(\d{1,4})\s*horas?\b",
                texto,
                re.IGNORECASE
            )

            if len(set(duraciones)) == 1:
                return padre

            # Si contiene varias duraciones, no lo consideramos fiable.
            if len(set(duraciones)) > 1:
                continue

    # Método 2: localizar bloques específicos de Elementor.
    #
    # En algunas páginas, el título y los bloques informativos no
    # comparten un contenedor directo. Se examinan entonces los bloques
    # que tienen una duración explícita.
    candidatos = []

    for bloque in soup.select(
        ".elementor-icon-box-content, "
        ".elementor-widget-container, "
        ".gsc-icon-box-content, "
        ".box-content"
    ):
        texto = re.sub(
            r"\s+",
            " ",
            bloque.get_text(" ", strip=True)
        ).strip()

        if not texto or len(texto) > 700:
            continue

        duraciones = re.findall(
            r"\b(\d{1,4})\s*horas?\b",
            texto,
            re.IGNORECASE
        )

        if len(set(duraciones)) != 1:
            continue

        # Debe ser un bloque con información explícita de modalidad
        # o duración, no un párrafo cualquiera.
        if not re.search(
            r"\b(?:presencial|teleformación|teleformacion|"
            r"online|duración|duracion|horas)\b",
            texto,
            re.IGNORECASE
        ):
            continue

        candidatos.append(bloque)

    if not candidatos:
        return None

    # Para evitar confundir cursos distintos, solo aceptamos un único
    # valor de duración entre los bloques informativos encontrados.
    horas_encontradas = set()

    for bloque in candidatos:
        horas_encontradas.update(
            re.findall(
                r"\b(\d{1,4})\s*horas?\b",
                bloque.get_text(" ", strip=True),
                re.IGNORECASE
            )
        )

    if len(horas_encontradas) == 1:
        return candidatos[0]

    logger.warning(
        "Hay varias duraciones posibles en la página de '%s': %s",
        titulo,
        sorted(horas_encontradas)
    )

    return None


def _extraer_horas(
    soup: BeautifulSoup,
    titulo: str = ""
) -> str:
    """
    Devuelve las horas únicamente cuando la duración es identificable.
    Una duración ambigua se deja vacía para no guardar un dato falso.
    """
    bloque = _buscar_bloque_curso(soup, titulo)

    if bloque is None:
        logger.warning(
            "No se encontró un bloque fiable para extraer la duración. "
            "Título: %s",
            titulo
        )
        return ""

    texto = bloque.get_text(" ", strip=True)

    coincidencias = re.findall(
        r"\b(\d{1,4})\s*horas?\b",
        texto,
        re.IGNORECASE
    )

    duraciones = list(dict.fromkeys(coincidencias))

    if len(duraciones) != 1:
        logger.warning(
            "Duración ausente o ambigua para '%s': %s",
            titulo,
            duraciones
        )
        return ""

    return f"{duraciones[0]} horas"


def _extraer_campo_estudio(
    titulo: str,
    texto_limpio: str
) -> str:
    combinado = _limpiar_texto(f"{titulo} {texto_limpio}")

    if any(k in combinado for k in [
        "informatic", "programac", "moodle", "digital",
        "software", "ciberseguridad", "redes", "html",
        "php", "python"
    ]):
        return "Informática y comunicaciones"

    if any(k in combinado for k in [
        "gestion", "administrac", "contabil",
        "recursos humanos", "ofimatica", "facturacion", "empresa"
    ]):
        return "Administración y gestión"

    if any(k in combinado for k in [
        "marketing", "comercial", "ventas",
        "atencion al cliente", "tienda"
    ]):
        return "Comercio y marketing"

    if any(k in combinado for k in [
        "sanid", "atencion sociosanitaria",
        "dependencia", "enfermer", "primeros auxilios"
    ]):
        return "Sanidad y servicios sociales"

    return "Formación Profesional y Empleo"


def _extraer_colectivo(texto_limpio: str) -> str:
    texto_limpio = _limpiar_texto(texto_limpio)

    if any(k in texto_limpio for k in [
        "desemplead", "trabajador", "demandante"
    ]):
        return "Personas desempleadas y trabajadoras"

    if "discapacidad" in texto_limpio:
        return "Personas con discapacidad"

    if "mayores" in texto_limpio or "jubilad" in texto_limpio:
        return "Mayores"

    return "General"


def _extraer_modalidad(texto_limpio: str) -> str:
    texto_limpio = _limpiar_texto(texto_limpio)

    if "teleformacion" in texto_limpio or "online" in texto_limpio:
        return "Teleformación"

    if "presencial" in texto_limpio:
        return "Presencial"

    return "General"


# ---------------------------------------------------------------------
# HTTP, URLs y contenido
# ---------------------------------------------------------------------

def _normalizar_url(url: str) -> str:
    return url.rstrip("/") + "/" if url else ""


def _es_url_curso_cefye(url: str) -> bool:
    """Solo admite URL HTTPS del dominio oficial y rutas de cursos."""
    parsed = urlparse(url)

    return (
        parsed.scheme == "https"
        and parsed.hostname in {DOMINIO_CEFYE, "cefye.com"}
        and re.fullmatch(r"/cursos/[^/]+/?", parsed.path) is not None
    )


def _extraer_enlaces_cursos(soup: BeautifulSoup) -> set:
    enlaces = set()

    for a in soup.find_all("a", href=True):
        url = urljoin(URL_BASE_CURSOS, a["href"])
        parsed = urlparse(url)

        url_limpia = parsed._replace(
            query="",
            fragment=""
        ).geturl()

        if not _es_url_curso_cefye(url_limpia):
            continue

        url_limpia = _normalizar_url(url_limpia)

        if url_limpia != _normalizar_url(URL_BASE_CURSOS):
            enlaces.add(url_limpia)

    return enlaces


def _crear_sesion_http():
    session = requests.Session()

    retries = Retry(
        total=5,
        connect=5,
        read=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True
    )

    adapter = HTTPAdapter(max_retries=retries)

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Connection": "keep-alive"
    })

    return session


def _extraer_contenido(soup: BeautifulSoup) -> str:
    """Extrae texto útil y excluye navegación, scripts y pie de página."""
    copia = BeautifulSoup(str(soup), "html.parser")

    for tag in copia.find_all([
        "nav", "header", "footer", "script", "style",
        "noscript", "iframe"
    ]):
        tag.decompose()

    principal = (
        copia.find("main")
        or copia.find("article")
        or copia.body
        or copia
    )

    fragmentos = []

    for tag in principal.find_all(["p", "li", "h2", "h3", "h4"]):
        texto = re.sub(
            r"\s+",
            " ",
            tag.get_text(" ", strip=True)
        ).strip()

        if texto and texto not in fragmentos:
            fragmentos.append(texto)

    return " ".join(fragmentos)


# ---------------------------------------------------------------------
# Comando de gestión de Django
# ---------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "ETL de cursos de CEFYE: extracción, staging, "
        "promoción y sincronización de registros."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Extrae y muestra resultados sin escribir en la base "
                "de datos ni desactivar cursos."
            )
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write("Iniciando proceso ETL de CEFYE...")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "MODO DRY-RUN: no se escribirán ni desactivarán registros."
                )
            )

        datos_crudos = []
        urls_404 = set()
        descartados = 0
        errores_extraccion = 0

        session = _crear_sesion_http()

        # -------------------------------------------------------------
        # 1. Extracción del índice de cursos
        # -------------------------------------------------------------

        try:
            response = session.get(
                _normalizar_url(URL_BASE_CURSOS),
                timeout=(10, 30)
            )
            response.raise_for_status()

            soup_index = BeautifulSoup(response.text, "html.parser")
            enlaces_cursos = _extraer_enlaces_cursos(soup_index)

            if not enlaces_cursos:
                raise RuntimeError(
                    "El índice de CEFYE no devolvió enlaces de cursos. "
                    "Se cancela el ETL para proteger la base de datos."
                )

            self.stdout.write(
                f"  Enlaces de cursos encontrados: {len(enlaces_cursos)}"
            )

        except Exception as exc:
            logger.exception("Error obteniendo el índice de CEFYE")
            session.close()

            raise RuntimeError(
                "No se pudo extraer el índice de cursos. "
                "No se ha realizado ninguna carga ni desactivación."
            ) from exc

        # -------------------------------------------------------------
        # 2. Extracción y transformación de cada curso
        # -------------------------------------------------------------

        try:
            for url_curso in sorted(enlaces_cursos):
                try:
                    response = session.get(
                        url_curso,
                        timeout=(10, 30),
                        allow_redirects=True
                    )

                    url_final = response.url

                    if urlparse(url_final).hostname not in {
                        DOMINIO_CEFYE, "cefye.com"
                    }:
                        logger.warning(
                            "Redirección fuera del dominio permitido: "
                            "%s -> %s",
                            url_curso,
                            url_final
                        )
                        errores_extraccion += 1
                        continue

                    if response.status_code == 404:
                        logger.warning("HTTP 404 en %s", url_curso)
                        urls_404.add(url_curso)
                        continue

                    if response.status_code != 200:
                        logger.warning(
                            "HTTP %s en %s",
                            response.status_code,
                            url_curso
                        )
                        errores_extraccion += 1
                        continue

                    soup_det = BeautifulSoup(
                        response.text,
                        "html.parser"
                    )

                    titulo = _extraer_titulo_curso(soup_det, url_curso)

                    if not titulo:
                        logger.warning(
                            "Curso descartado: título no identificado (%s)",
                            url_curso
                        )
                        descartados += 1
                        continue

                    provincia, localidad = _extraer_provincia_localidad(
                        soup_det
                    )

                    if provincia not in PROVINCIAS_CYL:
                        logger.info(
                            "Curso fuera de CyL: %s; provincia=%s",
                            url_curso,
                            provincia
                        )
                        descartados += 1
                        continue

                    contenido_completo = _extraer_contenido(soup_det)
                    texto_limpio = _limpiar_texto(contenido_completo)

                    modalidad = _extraer_modalidad(texto_limpio)
                    colectivo = _extraer_colectivo(texto_limpio)

                    campo_estudio = _extraer_campo_estudio(
                        titulo,
                        texto_limpio
                    )

                    horas = _extraer_horas(soup_det, titulo)

                    if not horas:
                        logger.warning(
                            "Curso extraído sin duración confirmada: %s",
                            url_curso
                        )

                    contenido_enriquecido = (
                        f"{contenido_completo} "
                        f"Provincia: {provincia}. "
                        f"Localidad: {localidad}. "
                        f"Modalidad: {modalidad}. "
                        f"Duración: {horas or 'No identificada'}. "
                        f"Colectivo: {colectivo}."
                    ).strip()

                    datos_crudos.append({
                        "titulo": titulo,
                        "contenido": contenido_enriquecido,
                        "provincia": provincia,
                        "localidad": localidad,
                        "campo_estudio": campo_estudio,
                        "colectivo": colectivo,
                        "url": url_curso,
                    })

                    self.stdout.write(
                        f"  [OK] {titulo} | {provincia} | "
                        f"{modalidad} | "
                        f"{horas or 'Duración no identificada'}"
                    )

                except Exception:
                    errores_extraccion += 1
                    logger.exception(
                        "Error procesando la URL %s",
                        url_curso
                    )
        finally:
            session.close()

        self.stdout.write("")
        self.stdout.write(
            f"Resultados de extracción: {len(datos_crudos)} válidos; "
            f"{descartados} descartados; "
            f"{len(urls_404)} respuestas 404; "
            f"{errores_extraccion} errores técnicos."
        )

        # -------------------------------------------------------------
        # 3. Validaciones antes de modificar datos
        # -------------------------------------------------------------

        if not datos_crudos:
            raise RuntimeError(
                "La extracción no ha producido cursos válidos. "
                "Se cancela el ETL sin modificar la base de datos."
            )

        extraccion_completa = errores_extraccion == 0

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY-RUN terminado: no se ha modificado la base de datos."
                )
            )
            return

        # -------------------------------------------------------------
        # 4. Carga a staging
        # -------------------------------------------------------------

        staging_ids = []
        errores_staging = 0

        for item in datos_crudos:
            try:
                url = _normalizar_url((item.get("url") or "").strip())

                if not url or url == "/":
                    logger.warning(
                        "Curso descartado del staging por URL vacía."
                    )
                    errores_staging += 1
                    continue

                hash_input = f"{url}|{item['titulo']}"
                hash_val = hashlib.sha256(
                    hash_input.encode("utf-8")
                ).hexdigest()

                defaults = {
                    "hash_contenido": hash_val,
                    "titulo_raw": item["titulo"],
                    "contenido_raw": item["contenido"],
                    "provincia_raw": item["provincia"],
                    "localidad": item["localidad"],
                    "campo_estudio_raw": item["campo_estudio"],
                    "colectivo_raw": item["colectivo"],
                    "estado": StagingCursos.PENDIENTE,
                }

                with transaction.atomic():
                    obj, _ = StagingCursos.objects.update_or_create(
                        url_oficial=url,
                        defaults=defaults,
                    )

                staging_ids.append(obj.pk)

            except (DatabaseError, ValueError, KeyError):
                logger.exception(
                    "Error guardando curso en staging: %s",
                    item.get("url")
                )
                errores_staging += 1

        self.stdout.write(
            f"  Staging: {len(staging_ids)} registros listos; "
            f"{errores_staging} errores."
        )

        # -------------------------------------------------------------
        # 5. Promoción a la base de conocimiento
        # -------------------------------------------------------------

        resultado = {
            "procesados": 0,
            "errores": 0,
            "ids_error": [],
        }

        if staging_ids:
            qs_a_promover = StagingCursos.objects.filter(
                pk__in=staging_ids,
                estado=StagingCursos.PENDIENTE
            )

            resultado = promover_staging(queryset=qs_a_promover)

            if resultado.get("errores"):
                self.stdout.write(
                    self.style.WARNING(
                        "Errores durante la promoción: "
                        f"{resultado.get('ids_error', [])}"
                    )
                )

        # -------------------------------------------------------------
        # 6. Desactivaciones protegidas
        # -------------------------------------------------------------

        desactivados_404 = 0
        desactivados_ausencia = 0

        if urls_404 and extraccion_completa:
            desactivados_404 = BaseConocimiento.objects.filter(
                url_oficial__in=urls_404,
                activo=True
            ).update(activo=False)

            if desactivados_404:
                self.stdout.write(
                    self.style.WARNING(
                        f"Desactivados por 404: {desactivados_404}"
                    )
                )

        elif urls_404:
            logger.warning(
                "Se omite la desactivación por 404 porque hubo errores "
                "técnicos durante la extracción."
            )

        if (
            extraccion_completa
            and errores_staging == 0
            and len(datos_crudos) >= MIN_CURSOS_PARA_DESACTIVAR
        ):
            urls_activas = {
                item["url"] for item in datos_crudos
            }

            desactivados_ausencia = (
                BaseConocimiento.objects
                .filter(activo=True)
                .exclude(url_oficial__in=urls_activas)
                .update(activo=False)
            )

        else:
            logger.warning(
                "Se omite la desactivación por ausencia. "
                "Extracción completa=%s; errores staging=%s; "
                "cursos válidos=%s; umbral=%s.",
                extraccion_completa,
                errores_staging,
                len(datos_crudos),
                MIN_CURSOS_PARA_DESACTIVAR
            )

        # -------------------------------------------------------------
        # 7. Resumen final
        # -------------------------------------------------------------

        total_errores = (
            errores_extraccion
            + errores_staging
            + resultado.get("errores", 0)
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"ETL completado: "
                f"{resultado.get('procesados', 0)} promovidos; "
                f"{desactivados_404 + desactivados_ausencia} desactivados "
                f"({desactivados_404} por 404; "
                f"{desactivados_ausencia} por ausencia); "
                f"{total_errores} errores."
            )
        )