"""Orquestador del bot: colectar -> detectar -> alertar -> guardar estado.

El nucleo del flujo vive en `correr()`, una funcion PURA: dados la config de
los paises, el estado previo y los resultados de la extraccion (texto o
SourceError), devuelve el nuevo estado y las alertas a notificar. Reglas
anti-ruido D10 (cooldown 24 h, tope de embeds) viven aca, testeables sin red.

El ruteo a Discord usa 2 canales (D9): publico para apertura/cierre,
admin para cambio/fuente_inaccesible (PLAN §8).
"""

from __future__ import annotations

import datetime
import os
import sys
import time
from dataclasses import replace

import httpx

from src.collectors.base import SourceError, fetch_page
from src.collectors.browser import fetch_page_navegador
from src.collectors.scraper import extraer
from src.config import CountryConfig, load_alertas_config, load_countries
from src.detection import decidir, decidir_fallo, evidencia
from src.notify import construir_mensaje, enviar
from src.state import Snapshot, cargar, guardar

Resultado = str | SourceError
ALERTABLES = {"apertura", "cierre", "cambio", "fuente_inaccesible"}
# D9: ruteo por tipo de alerta a canal publico (comunidad) o admin (staff).
RUTEO = {
    "apertura": "publico",
    "cierre": "publico",
    "cambio": "admin",
    "fuente_inaccesible": "admin",
}
# D10: prioridad cuando hay mas alertas que el tope de embeds.
PRIORIDAD = ["apertura", "cierre", "fuente_inaccesible", "cambio"]
PAUSA_ENTRE_ENVIOS = 1.0  # s: cortesia con el rate limit de Discord
LARGO_EXTRACTO_CAMBIO = 120


def correr(
    paises: dict,
    estado_previo: dict[str, Snapshot],
    resultados: dict[str, Resultado],
    ahora: str = "",
    cooldown_horas: int = 24,
    max_embeds: int = 3,
) -> tuple[dict[str, Snapshot], list[tuple[str, str]]]:
    """Procesa los resultados de una corrida.

    Devuelve (nuevo_estado, alertas) donde alertas es [(codigo, tipo_decision)]
    ya filtrada por cooldown (D10) y recortada al tope de embeds con
    prioridad. Reglas: siembra silenciosa (R1), fallos consecutivos (R3) y un
    pais caido no bloquea a los demas (R4).
    """
    ahora_iso = ahora or datetime.datetime.now(datetime.UTC).isoformat()
    nuevo_estado: dict[str, Snapshot] = dict(estado_previo)
    alertas: list[tuple[str, str]] = []

    for codigo, pais in paises.items():
        anterior = nuevo_estado.get(codigo)
        resultado = resultados[codigo]
        base = anterior or Snapshot(estado="desconocido", texto="")

        if isinstance(resultado, SourceError):
            decision = decidir_fallo(base.fallas_consecutivas)
            fallas = 0 if decision.tipo == "fuente_inaccesible" else (
                base.fallas_consecutivas + 1
            )
            nuevo_estado[codigo] = replace(
                base,
                fallas_consecutivas=fallas,
                actualizado_en=ahora_iso,
            )
        else:
            decision = decidir(pais, anterior, resultado)
            nuevo_estado[codigo] = replace(
                base,
                estado=decision.estado or base.estado,
                texto=resultado,
                fallas_consecutivas=0,
                actualizado_en=ahora_iso,
            )

        notificable = decision.tipo in ALERTABLES and not _en_cooldown(
            base, decision.tipo, ahora_iso, cooldown_horas
        )
        if notificable:
            alertas.append((codigo, decision.tipo))
            nuevo_estado[codigo] = replace(
                nuevo_estado[codigo],
                alertas_enviadas=_marcar_enviada(
                    base.alertas_enviadas, decision.tipo, ahora_iso
                ),
            )

    return nuevo_estado, seleccionar_alertas(alertas, max_embeds)


def _en_cooldown(
    snapshot: Snapshot, tipo: str, ahora_iso: str, cooldown_horas: int
) -> bool:
    """D10: True si ya se notifico `tipo` para este pais hace < cooldown_horas."""
    if cooldown_horas <= 0:
        return False
    ultima = snapshot.alertas_enviadas.get(tipo)
    if not ultima:
        return False
    try:
        anterior = datetime.datetime.fromisoformat(ultima)
        presente = datetime.datetime.fromisoformat(ahora_iso)
        transcurrido = presente - anterior
    except (ValueError, TypeError):
        return False
    return transcurrido < datetime.timedelta(hours=cooldown_horas)


def _marcar_enviada(enviadas: dict[str, str], tipo: str, ahora_iso: str) -> dict[str, str]:
    marcadas = dict(enviadas)
    marcadas[tipo] = ahora_iso
    return marcadas


def seleccionar_alertas(
    alertas: list[tuple[str, str]], max_embeds: int
) -> list[tuple[str, str]]:
    """D10: recorta al tope priorizando apertura > cierre > fuente > cambio."""
    if max_embeds <= 0:
        return sorted(alertas, key=lambda alerta: PRIORIDAD.index(alerta[1]))
    return sorted(alertas, key=lambda alerta: PRIORIDAD.index(alerta[1]))[:max_embeds]


def cita_para(tipo: str, pais: CountryConfig, snapshot: Snapshot | None) -> str:
    """D10: evidencia literal para el embed, segun el tipo de alerta."""
    if snapshot is None:
        return ""
    if tipo == "apertura":
        return evidencia(snapshot.texto, pais.keywords_abierto)
    if tipo == "cierre":
        return evidencia(snapshot.texto, pais.keywords_cerrado)
    if tipo == "cambio":
        return snapshot.texto[:LARGO_EXTRACTO_CAMBIO]
    return ""  # fuente_inaccesible: no hay texto de fuente que citar


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


def notificar(
    alertas: list[tuple[str, str]],
    paises: dict,
    estado: dict[str, Snapshot],
    webhooks: dict[str, str],
    pausa_segundos: float = PAUSA_ENTRE_ENVIOS,
) -> int:
    """Envia un embed por alerta al canal que corresponde (D9).

    Devuelve cuantos envios fallaron. Canal sin webhook -> la alerta queda
    en el log y se cuenta como pendiente (nunca se filtra al otro canal).
    """
    fallas = 0
    with httpx.Client() as client:
        for indice, (codigo, tipo) in enumerate(alertas):
            destino = webhooks.get(RUTEO[tipo], "")
            if not destino:
                print(f"  sin canal '{RUTEO[tipo]}': {codigo}:{tipo} queda en log")
                fallas += 1
                continue
            payload = construir_mensaje(
                paises[codigo],
                tipo,
                cita=cita_para(tipo, paises[codigo], estado.get(codigo)),
            )
            if indice and pausa_segundos:
                time.sleep(pausa_segundos)
            if not enviar(destino, payload, client):
                fallas += 1
                print(f"  fallo el envio a Discord de {codigo}:{tipo}")
    return fallas


def main() -> int:
    """Punto de entrada: SIEMPRE termina con exit 0 para no romper el cron."""
    paises = load_countries()
    alertas_config = load_alertas_config()
    estado_previo = cargar()

    with httpx.Client() as client:
        resultados = recolectar(paises, client)

    estado_nuevo, alertas = correr(
        paises,
        estado_previo,
        resultados,
        cooldown_horas=alertas_config.cooldown_horas,
        max_embeds=alertas_config.max_embeds_corrida,
    )
    guardar(estado_nuevo)

    webhooks = {
        "publico": os.getenv("DISCORD_WEBHOOK_URL", ""),
        "admin": os.getenv("DISCORD_WEBHOOK_ADMIN_URL", ""),
    }
    fallas_envio = notificar(alertas, paises, estado_nuevo, webhooks)
    resumen_alertas = "; ".join(
        f"{codigo}:{tipo}" for codigo, tipo in alertas
    ) or "ninguna"
    print(f"corrida completa | alertas: {resumen_alertas} | envios fallidos: {fallas_envio}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
