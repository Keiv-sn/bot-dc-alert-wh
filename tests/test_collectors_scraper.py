"""Tests del scraper: extraccion de texto normalizado, por fila ancla o selector CSS.

Los casos de Australia y Nueva Zelanda usan los fixtures REALES de la Etapa 2
(tests/fixtures/*.html) como fuente de verdad.
"""

from pathlib import Path

import pytest

from src.collectors.base import SourceError
from src.collectors.scraper import (
    extract_row_text,
    extract_selector_text,
    extract_text,
    extraer,
)
from src.config import CountryConfig

FIXTURES = Path(__file__).parent / "fixtures"


class TestExtractText:
    def test_normaliza_espacios_y_salta_scripts(self) -> None:
        html = b"""<html><head><style>.x { color: red }</style></head>
            <body><h1>  Convocatoria   </h1><script>malicioso()</script>
            <p>chile     Australia</p></body></html>"""
        texto = extract_text(html)
        assert "Convocatoria" in texto
        assert "chile Australia" in texto
        assert "malicioso()" not in texto
        assert "color: red" not in texto
        assert "\n" not in texto

    def test_acepta_cualquier_encoding_y_no_rompe(self) -> None:
        # fixture japones con encoding distinto: debe procesar sin excepcion
        texto = extract_text((FIXTURES / "jp.html").read_bytes())
        assert len(texto) > 100
        assert "\n" not in texto

    def test_elimina_caracteres_invisibles(self) -> None:
        html = "<p>Chile\u200bOpen \u00a03,400</p>".encode("utf-8")
        assert extract_text(html) == "Chile Open 3,400"


class TestFilaAncla:
    def test_fila_de_chile_australia_dada_fixture_real(self) -> None:
        html = (FIXTURES / "au.html").read_bytes()
        fila = extract_row_text(html, "Chile")
        assert fila is not None
        assert "Open" in fila
        assert "3,400" in fila

    def test_ancla_inexistente_devuelve_none(self) -> None:
        fila = extract_row_text(b"<table><tr><td>Canada</td></tr></table>", "Chile")
        assert fila is None


class TestSelectorCss:
    def test_estado_nueva_zelanda_dada_fixture_real(self) -> None:
        html = (FIXTURES / "nz.html").read_bytes()
        texto = extract_selector_text(html, ".visa-page__status-wrapper")
        assert texto is not None
        assert "closed for 2026" in texto.lower()

    def test_selector_sin_match_devuelve_none(self) -> None:
        texto = extract_selector_text(b"<html><body></body></html>", ".no-existo")
        assert texto is None


class TestDispatcher:
    """`extraer()` según el metodo declarado en la config del pais."""

    AU_FILA = (FIXTURES / "au.html").read_bytes()

    def test_metodo_texto(self) -> None:
        texto = extraer(_pais("texto"), b"<html><body><p>convocatoria</p></body></html>")
        assert texto == "convocatoria"

    def test_metodo_fila_con_fixture_australia(self) -> None:
        fila = extraer(_pais("fila", ancla="Chile"), self.AU_FILA)
        assert "Open" in fila

    def test_metodo_fila_sin_ancla_da_estructura(self) -> None:
        with pytest.raises(SourceError) as info:
            extraer(_pais("fila", ancla="Noexiste"), self.AU_FILA)
        assert info.value.codigo == "estructura"


def _pais(metodo: str, ancla: str = "") -> CountryConfig:
    return CountryConfig(
        codigo="au", nombre="Australia", url="https://x", metodo=metodo, ancla=ancla,
    )
