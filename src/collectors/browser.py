"""Colector con Chromium headful (Playwright) para fuentes con WAF.

Nivel 4 de docs/PLAN.md §4: fuentes que bloquean clientes HTTP (Incapsula de
NZ, huella TLS de .go.jp, CDN de canada.ca) pero aceptan un navegador real.
La primera pasada entrega cookies del challenge; el reload siguiente ya llega
con acceso. Emite SourceError con los mismos codigos que collectors/base.py.
"""

from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from src.collectors.base import SourceError

TIMEOUT_NAVEGADOR = 45_000  # ms
ESPERA_POST_CARGA = 6_000  # ms: deja ejecutar el challenge y scripts
INTENTOS_DE_CHALLENGE = 3  # reloads maximos con cookies ganadas
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


def fetch_page_navegador(url: str, timeout_ms: int = TIMEOUT_NAVEGADOR) -> str:
    """Abre `url` en Chromium headful y devuelve el HTML final renderizado."""
    respuesta = None
    try:
        with sync_playwright() as playwright:
            navegador = playwright.chromium.launch(
                headless=False,
                args=["--disable-blink-features=AutomationControlled"],
            )
            pagina = navegador.new_page(user_agent=USER_AGENT)
            pagina.add_init_script(_ocultar_webdriver())
            respuesta = pagina.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
            pagina.wait_for_timeout(ESPERA_POST_CARGA)
            contenido = _superar_challenge(pagina, timeout_ms)
            navegador.close()
    except PlaywrightError as error:
        raise SourceError("red", f"fallo de navegador en {url}: {error}") from None

    if respuesta is None:
        raise SourceError("http_status", f"sin respuesta en {url}")
    if respuesta.status != 200:
        raise SourceError("http_status", f"status {respuesta.status} en {url}")
    if not contenido.strip():
        raise SourceError("vacio", f"pagina sin contenido en {url}")
    return contenido


def _ocultar_webdriver() -> str:
    """Script que evita la deteccion basica de `navigator.webdriver`."""
    return "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"


def _es_pagina_de_challenge(html: str) -> bool:
    """Challenge activo = respuesta corta o marca de Incapsula."""
    return "Incapsula" in html or len(html) < 2_000


def _superar_challenge(pagina, timeout_ms: int) -> str:
    """Recarga mientras el challenge siga activo; devuelve el HTML final."""
    contenido = pagina.content()
    for _ in range(INTENTOS_DE_CHALLENGE):
        if not _es_pagina_de_challenge(contenido):
            break
        try:
            pagina.reload(timeout=timeout_ms, wait_until="domcontentloaded")
        except PlaywrightError:
            break  # el sitio cerro la pestana; seguimos con lo ultimo sabido
        pagina.wait_for_timeout(ESPERA_POST_CARGA)
        contenido = pagina.content()
    return contenido
