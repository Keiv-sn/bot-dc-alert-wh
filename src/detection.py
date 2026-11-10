"""Motor de deteccion: clasifica documentos, compara con el estado previo y decide.

Decisiones posibles (tipos): siembra, sin_cambios, apertura, cierre, cambio,
ignore, fuente_inaccesible. Solo apertura/cierre/cambio/fuente_inaccesible
se notifican (docs/PLAN.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from src.config import CountryConfig
from src.state import Snapshot

UMBRAL_DE_FALLOS = 2  # regla R3: se nota solo a partir del 2do fallo consecutivo


@dataclass(frozen=True)
class Decision:
    tipo: str
    estado: str  # estado clasificado del nuevo documento ("" cuando no aplica)
    detalle: str = ""


def clasificar(texto: str, pais: CountryConfig) -> str:
    """Aplica las keywords del pais al texto normalizado."""
    texto = texto.lower()
    abierto = any(keyword in texto for keyword in pais.keywords_abierto)
    cerrado = any(keyword in texto for keyword in pais.keywords_cerrado)
    if abierto and not cerrado:
        return "abierto"
    if cerrado and not abierto:
        return "cerrado"
    return "desconocido"


def decidir(pais: CountryConfig, snapshot: Snapshot | None, texto: str) -> Decision:
    """Compara el documento nuevo con el snapshot previo del pais."""
    estado_nuevo = clasificar(texto, pais)

    if snapshot is None or not snapshot.texto.strip():
        # ninguna corrida real se concretó aún (R1): guardar sin notificar
        return Decision("siembra", estado_nuevo, "primera corrida real del pais")
    if texto.strip() == snapshot.texto.strip():
        return Decision("sin_cambios", snapshot.estado)
    if estado_nuevo == "abierto" and snapshot.estado != "abierto":
        return Decision("apertura", "abierto", f"antes: {snapshot.estado}")
    if estado_nuevo == "cerrado" and snapshot.estado != "cerrado":
        return Decision("cierre", "cerrado", f"antes: {snapshot.estado}")
    return Decision("cambio", estado_nuevo, "texto cambio sin cambio de estado")


def decidir_fallo(fallas_previas: int, umbral: int = UMBRAL_DE_FALLOS) -> Decision:
    """Regla R3: un fallo es ruido; fallos consecutivos >= umbral son señal."""
    if fallas_previas + 1 >= umbral:
        return Decision("fuente_inaccesible", estado="", detalle=f"{umbral} fallos seguidos")
    return Decision("ignore", estado="")
