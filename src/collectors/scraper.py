"""Scraper: convierte HTML de una fuente oficial en texto relevante.

Tres metodos de extraccion, elegidos por pais en config/countries.toml:
- texto    : toda la pagina (uma moncdeteccion por keywords difusas)
- fila     : la fila <tr> que contiene un texto ancla (Australia: 'Chile')
- selector : el elemento que matchea un selector CSS (NZ: '.visa-page__status')
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

ETIQUETAS_RUIDO = ["script", "style", "noscript"]


def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def extract_text(html: bytes) -> str:
    """Texto normalizado de toda la pagina (sin scripts ni estilos)."""
    soup = BeautifulSoup(html, "html.parser")
    for etiqueta in soup(ETIQUETAS_RUIDO):
        etiqueta.decompose()
    return _limpiar(soup.get_text(" ", strip=True))


def extract_row_text(html: bytes, ancla: str) -> str | None:
    """Texto normalizado de la primera fila <tr> que contiene `ancla`.

    Usado cuando la pagina es una tabla de paises (Australia).
    """
    soup = BeautifulSoup(html, "html.parser")
    for fila in soup.find_all("tr"):
        if ancla in fila.get_text(" ", strip=True):
            return _limpiar(fila.get_text(" ", strip=True))
    return None


def extract_selector_text(html: bytes, selector_css: str) -> str | None:
    """Texto del primer elemento que matchea `selector_css` (p. ej. NZ)."""
    soup = BeautifulSoup(html, "html.parser")
    elemento = soup.select_one(selector_css)
    if elemento is None:
        return None
    for etiqueta in elemento(ETIQUETAS_RUIDO):
        etiqueta.decompose()
    return _limpiar(elemento.get_text(" ", strip=True))
