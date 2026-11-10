"""Tests del colector base: HTTP con headers de navegador, errores clasificados
y un solo reintento para fallos de red/timeout (docs/PLAN.md Etapa 2)."""

import httpx
import pytest

from src.collectors.base import SourceError, fetch_page

ACCESO = "http://test/convocatoria"


class ClienteFalso:
    """Sustituto determinista de httpx.Client para tests."""

    def __init__(self, respuestas: list) -> None:
        self.respuestas = list(respuestas)
        self.llamadas: list = []

    def get(self, url: str, **kwargs):
        self.llamadas.append({"url": url, **kwargs})
        item = self.respuestas.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class RespuestaFalsa:
    def __init__(self, status_code: int = 200, text: str = "<html>ok</html>") -> None:
        self.status_code = status_code
        self.text = text


def test_200_devuelve_html() -> None:
    cliente = ClienteFalso([RespuestaFalsa(200, "<html>convocatoria</html>")])

    html = fetch_page(ACCESO, cliente)

    assert html == "<html>convocatoria</html>"
    llamada = cliente.llamadas[0]
    assert llamada["url"] == ACCESO
    assert "Mozilla" in llamada["headers"]["User-Agent"]
    assert llamada["follow_redirects"] is True


def test_403_no_reintenta_y_lanza_http_status() -> None:
    cliente = ClienteFalso([RespuestaFalsa(403, "denegado")])

    with pytest.raises(SourceError) as exc_info:
        fetch_page(ACCESO, cliente)

    assert exc_info.value.codigo == "http_status"
    assert len(cliente.llamadas) == 1  # reintentar un 403 no ayuda


def test_html_vacio_lanza_vacio() -> None:
    cliente = ClienteFalso([RespuestaFalsa(200, "   ")])
    with pytest.raises(SourceError) as exc_info:
        fetch_page(ACCESO, cliente)
    assert exc_info.value.codigo == "vacio"


def test_timeout_reintenta_una_vez_y_lanza_red() -> None:
    cliente = ClienteFalso(
        [
            httpx.TimeoutException("t1"),
            httpx.TimeoutException("t2"),
        ]
    )
    with pytest.raises(SourceError) as exc_info:
        fetch_page(ACCESO, cliente)
    assert exc_info.value.codigo == "red"
    assert len(cliente.llamadas) == 2  # intento + 1 reintento


def test_timeout_en_primer_intento_y_exito_en_segundo() -> None:
    cliente = ClienteFalso(
        [
            httpx.TimeoutException("t1"),
            RespuestaFalsa(200, "<html>recuperada</html>"),
        ]
    )
    html = fetch_page(ACCESO, cliente)
    assert html == "<html>recuperada</html>"
    assert len(cliente.llamadas) == 2


def test_error_de_red_reintenta_y_lanza_red() -> None:
    cliente = ClienteFalso([httpx.NetworkError("n1"), httpx.NetworkError("n2")])
    with pytest.raises(SourceError) as exc_info:
        fetch_page(ACCESO, cliente)
    assert exc_info.value.codigo == "red"
