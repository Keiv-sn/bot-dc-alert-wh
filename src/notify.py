"""Notificaciones Discord: payload por tipo de alerta + envio tolerante.

El envio nunca tumba la corrida: fallos de Discord devuelven False y quedan
en el log (docs/PLAN.md §8 y el exit 0 garantizado del orquestador).
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from src.config import CountryConfig

SANTIAGO = ZoneInfo("America/Santiago")
TIMEOUT_WEBHOOK = 15.0

COLORES = {
    "apertura": 0x57F287,  # verde
    "cierre": 0xED4245,  # rojo
    "cambio": 0xFEE75C,  # amarillo
    "fuente_inaccesible": 0x99AAB5,  # gris
}
ICONOS = {
    "apertura": "🟢",
    "cierre": "🔴",
    "cambio": "🔄",
    "fuente_inaccesible": "⚠️",
}
TITULOS = {
    "apertura": "Convocatoria ABIERTA",
    "cierre": "Convocatoria CERRADA",
    "cambio": "Cambio en la página",
    "fuente_inaccesible": "Fuente inaccesible",
}
TEXTOS = {
    "apertura": (
        "La convocatoria de Working Holiday está abierta. Revisa la fuente oficial "
        "y postula a tiempo: los cupos suelen agotarse rápido."
    ),
    "cierre": "La convocatoria pasó a estado cerrado. No es posible postular en este momento.",
    "cambio": (
        "El contenido de la página oficial cambió sin abrir ni cerrar la convocatoria. "
        "En revisión por administración."
    ),
    "fuente_inaccesible": (
        "La fuente oficial no respondió en corridas consecutivas. "
        "Administración verificará el acceso."
    ),
}
FOOTER = "WH Alerts Chile · detección automática — verifica en la fuente"


def construir_mensaje(
    pais: CountryConfig,
    tipo: str,
    detalle: str = "",
    cita: str = "",
    ahora: datetime | None = None,
) -> dict:
    """Payload de Discord (embed) para la alerta de un pais.

    D10 (PLAN §8): incluye "Detectado" (hora de Chile) y, si hay `cita`,
    la evidencia literal de la fuente. `allowed_mentions` vacio garantiza
    que NINGUN mensaje pueda mencionar usuarios o roles.
    """
    instante = ahora or datetime.now(UTC)
    titulo = f"{ICONOS[tipo]} {TITULOS[tipo]} — {pais.nombre}"
    partes = [TEXTOS[tipo]]
    if detalle:
        partes.append(f"_({detalle})_")

    campos = [
        {
            "name": "Detectado",
            "value": f"{hora_chile(instante.isoformat())} (hora de Chile)",
            "inline": True,
        }
    ]
    if cita:
        campos.append(
            {
                "name": "Evidencia (texto de la fuente)",
                "value": f"«{cita}»",
                "inline": False,
            }
        )

    return {
        "allowed_mentions": {"parse": []},
        "embeds": [
            {
                "title": titulo,
                "description": "\n".join(partes),
                "color": COLORES[tipo],
                "url": pais.url,
                "timestamp": instante.isoformat(),
                "fields": campos,
                "footer": {"text": FOOTER},
            }
        ],
    }


def hora_chile(iso_utc: str) -> str:
    """Convierte un ISO (UTC o invalido) a 'HH:MM del dd/mm' de Santiago."""
    try:
        instante = datetime.fromisoformat(iso_utc)
    except ValueError:
        return ""
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=UTC)
    local = instante.astimezone(SANTIAGO)
    return local.strftime("%H:%M del %d/%m")


def enviar(webhook_url: str, payload: dict, client) -> bool:
    """POST al webhook con 1 reintento; True solo si Discord respondio 2xx."""
    for _ in range(2):
        try:
            respuesta = client.post(webhook_url, json=payload, timeout=TIMEOUT_WEBHOOK)
        except Exception:  # noqa: BLE001 — cualquier fallo de red se reintenta una vez
            continue
        if 200 <= respuesta.status_code < 300:
            return True
    return False
