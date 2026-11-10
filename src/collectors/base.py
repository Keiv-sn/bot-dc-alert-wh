"""Colector base: obtiene el HTML de una fuente oficial con errores clasificados.

Errores se clasifican con SourceError (codigo: 'http_status', 'vacio' o 'red')
para que el motor de deteccion pueda decidir sin ambiguedad (docs/PLAN.md R3):
un fallo de la fuente NUNCA es un cambio de convocatoria.
"""

from __future__ import annotations

import httpx

HEADERS_NAVEGADOR = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-CL,es;q=0.9,en;q=0.8",
}

TIMEOUT_SEGUNDOS = 30.0
INTENTOS_DE_RED = 2  # 1 intento + 1 reintento para fallos de red/timeout


class SourceError(Exception):
    """Fallo conocido al obtener una fuente, semaforo del motor de deteccion."""

    def __init__(self, codigo: str, detalle: str = "") -> None:
        self.codigo = codigo
        self.detalle = detalle
        super().__init__(f"[{codigo}] {detalle}")


def fetch_page(
    url: str,
    client: httpx.Client,
    timeout: float = TIMEOUT_SEGUNDOS,
) -> str:
    """Descarga `url` con headers de navegador y devuelve el HTML crudo.

    - Errores de estado HTTP (403/500...): un solo intento, no se reintenta.
    - Errores de red o timeout: se reintenta una vez antes de fallar.
    """
    ultimo_fallo_de_red: SourceError | None = None

    for _ in range(INTENTOS_DE_RED):
        try:
            respuesta = client.get(
                url,
                headers=HEADERS_NAVEGADOR,
                timeout=timeout,
                follow_redirects=True,
            )
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            ultimo_fallo_de_red = SourceError("red", str(exc))
            continue

        if respuesta.status_code != 200:
            raise SourceError(
                "http_status",
                f"status {respuesta.status_code} en {url}",
            )
        if not respuesta.text.strip():
            raise SourceError("vacio", f"respuesta sin contenido en {url}")
        return respuesta.text

    assert ultimo_fallo_de_red is not None  # siempre hay un fallo al llegar aqui
    raise ultimo_fallo_de_red from None
