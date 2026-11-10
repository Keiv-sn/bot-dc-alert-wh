"""Orquestador del bot: colectar -> detectar -> alertar -> guardar estado.

El nucleo del flujo vive en `correr()`, una funcion PURA: dados la config de
los paises, el estado previo y los resultados de la extraccion (texto o
SourceError), devuelve el nuevo estado y las alertas a notificar. Toda la
regla de negocio es testeable sin red, sin archivos y sin Discord.
"""

from __future__ import annotations

import datetime
import sys
from dataclasses import replace

import httpx

from src.collectors.base import SourceError, fetch_page
from src.collectors.browser import fetch_page_navegador
from src.collectors.scraper import extraer
from src.config import load_countries
from src.detection import decidir, decidir_fallo
from src.state import Snapshot, cargar, guardar

Resultado = str | SourceError
ALERTABLES = {"apertura", "cierre", "cambio", "fuente_inaccesible"}


def correr(
    paises: dict,
    estado_previo: dict[str, Snapshot],
    resultados: dict[str, Resultado],
    ahora: str = "",
) -> tuple[dict[str, Snapshot], list[tuple[str, str]]]:
    """Procesa los resultados de una corrida.

    Devuelve (nuevo_estado, alertas) donde alertas es [(codigo, tipo_decision)].
    Reglas: siembra silenciosa (R1), fallos consecutivos (R3) y un pais caido
    no bloquea a los demas (R4).
    """
    ahora_iso = ahora or datetime.datetime.now(datetime.UTC).isoformat()
    nuevo_estado: dict[str, Snapshot] = dict(estado_previo)
    alertas: list[tuple[str, str]] = []

    for codigo, pais in paises.items():
        anterior = nuevo_estado.get(codigo)
        resultado = resultados[codigo]

        if isinstance(resultado, SourceError):
            decision = decidir_fallo(anterior.fallas_consecutivas if anterior else 0)
            base = anterior or Snapshot(estado="desconocido", texto="")
            fallas = 0 if decision.tipo == "fuente_inaccesible" else (
                base.fallas_consecutivas + 1
            )
        else:
            decision = decidir(pais, anterior, resultado)
            base = anterior or Snapshot(estado="desconocido", texto="")
            fallas = 0
            nuevo_estado[codigo] = replace(
                base,
                estado=decision.estado or base.estado,
                texto=resultado,
                fallas_consecutivas=0,
                actualizado_en=ahora_iso,
            )

        if isinstance(resultado, SourceError):
            nuevo_estado[codigo] = replace(
                base,
                fallas_consecutivas=fallas,
                actualizado_en=ahora_iso,
            )

        if decision.tipo in ALERTABLES:
            alertas.append((codigo, decision.tipo))

    return nuevo_estado, alertas


def recolectar(paises: dict, client: httpx.Client) -> dict[str, Resultado]:
    """Descarga y extrae cada pais: texto extraido o SourceError, sin excepciones."""
    resultados: dict[str, Resultado] = {}
    for codigo, pais in paises.items():
        try:
            if pais.acceso == "navegador":
                html = fetch_page_navegador(pais.url)
            else:
                html = fetch_page(pais.url, client)
            resultados[codigo] = extraer(pais, html)
        except SourceError as error:
            resultados[codigo] = error
    return resultados


def main() -> int:
    """Punto de entrada: SIEMPRE termina con exit 0 para no romper el cron."""
    paises = load_countries()
    estado_previo = cargar()

    with httpx.Client() as client:
        resultados = recolectar(paises, client)

    estado_nuevo, alertas = correr(paises, estado_previo, resultados)
    guardar(estado_nuevo)

    mensaje_alerta = "; ".join(
        f"{codigo}:{tipo}" for codigo, tipo in alertas
    ) or "ninguna"
    print(f"corrida completa | alertas: {mensaje_alerta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
