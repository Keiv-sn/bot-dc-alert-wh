"""Scraper: convierte HTML de una fuente oficial en texto relevante.

Tres metodos de extraccion, elegidos por pais en config/countries.toml:
- texto    : toda la pagina (deteccion por keywords sobre el texto crudo)
- fila     : la fila <tr> que contiene un texto ancla (Australia: 'Chile')
- selector : el elemento que matchea un selector CSS (NZ: '.visa-page__status')
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from src.collectors.base import SourceError
from src.config import CountryConfig

ETIQUETAS_RUIDO = ["script", "style", "noscript"]
# caracteres invisibles que ensucian comparaciones de texto entre fuentes
CARACTERES_FANTASMA = {"\u200b": " ", "\u00a0": " ", "\u200e": " ", "\u200f": ""}
TRANS_TABLA = str.maketrans(CARACTERES_FANTASMA)

META_CHARSET = re.compile(rb"charset\s*=\s*[\"']?([\w-]+)", re.IGNORECASE)


def _a_texto(html: str | bytes) -> str:
    """bytes a str respetando el charset declarado; utf-8 como alternativa."""
    if isinstance(html, str):
        return html
    match_charset = META_CHARSET.search(html)
    if match_charset:
        try:
            return html.decode(match_charset.group(1).decode("ascii"))
        except (LookupError, UnicodeDecodeError):
            pass
    return html.decode("utf-8", errors="replace")


def _limpiar(texto: str) -> str:
    texto = texto.translate(TRANS_TABLA)
    return re.sub(r"\s+", " ", texto).strip()


def _soup(html: str | bytes) -> BeautifulSoup:
    return BeautifulSoup(_a_texto(html), "html.parser")


def extract_text(html: str | bytes) -> str:
    """Texto normalizado de toda la pagina (sin scripts ni estilos)."""
    soup = _soup(html)
    for etiqueta in soup(ETIQUETAS_RUIDO):
        etiqueta.decompose()
    return _limpiar(soup.get_text(" ", strip=True))


def extract_row_text(html: str | bytes, ancla: str) -> str | None:
    """Texto normalizado de la primera fila <tr> que contiene `ancla`.

    Usado cuando la pagina es una tabla de paises (Australia).
    """
    soup = _soup(html)
    for fila in soup.find_all("tr"):
        if ancla in fila.get_text(" ", strip=True):
            return _limpiar(fila.get_text(" ", strip=True))
    return None


def extract_selector_text(html: str | bytes, selector_css: str) -> str | None:
    """Texto del primer elemento que matchea `selector_css` (p. ej. NZ)."""
    soup = _soup(html)
    elemento = soup.select_one(selector_css)
    if elemento is None:
        return None
    for etiqueta in elemento(ETIQUETAS_RUIDO):
        etiqueta.decompose()
    return _limpiar(elemento.get_text(" ", strip=True))


def extraer(pais: CountryConfig, html: str | bytes) -> str:
    """Texto relevante segun el `metodo` declarado para el pais.

    Si fila/selector no matchean nada, la estructura de la pagina cambio:
    se reporta como SourceError('estructura'), igual que una pagina caida.
    """
    if pais.metodo == "texto":
        return extract_text(html)
    if pais.metodo == "fila":
        resultado = extract_row_text(html, pais.ancla)
    else:
        resultado = extract_selector_text(html, pais.selector)
    if resultado is None:
        raise SourceError(
            "estructura",
            f"no se encontro {'ancla' if pais.metodo == 'fila' else 'selector'} "
            f"'{pais.ancla or pais.selector}' de {pais.codigo}",
        )
    return resultado
