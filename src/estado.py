"""Renderizador del estado de los programas + CLI de terminal (solo lectura).

Una sola fuente de verdad para las lineas de estado: la usa este CLI
(`python -m src.estado`, opcion A: revision rapida local) y el digest diario
que el bot manda al canal admin (opcion C, via src/notify.py). Puro: solo lee
config/countries.toml y data/state.json; no toca la red ni Discord.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

from src.config import RUTA_CONFIG_DEFECTO, CountryConfig, load_countries
from src.state import RUTA_DEFECTO, Snapshot, cargar

LARGO_CITA = 60
ETIQUETAS = {
    "abierto": "🟢 ABIERTO",
    "cerrado": "🔴 CERRADO",
    "desconocido": "⚪ DESCONOCIDO",
}
ETIQUETA_SIN_DATOS = "⚪ SIN DATOS"


def hace_cuanto(actualizado_en: str, ahora: datetime) -> str:
    """Diferencia legible ('hace 3 h', 'hace 3 d') desde el ISO guardado."""
    if not actualizado_en:
        return "sin datos"
    try:
        anterior = datetime.fromisoformat(actualizado_en)
    except ValueError:
        return "sin datos"
    if anterior.tzinfo is None:
        anterior = anterior.replace(tzinfo=UTC)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=UTC)
    horas = int((ahora - anterior).total_seconds() // 3600)
    if horas < 1:  # incluye timestamps futuros (relojes desincronizados)
        return "hace menos de 1 h"
    if horas < 48:
        return f"hace {horas} h"
    return f"hace {horas // 24} d"


def cita_corta(texto: str, largo: int = LARGO_CITA) -> str:
    """Primer fragmento legible del texto de la fuente, en una sola linea."""
    plano = " ".join(texto.split())
    if not plano:
        return ""
    if len(plano) <= largo:
        return plano
    return f"{plano[:largo]}…"


def linea_pais(pais: CountryConfig, snapshot: Snapshot | None, ahora: datetime) -> str:
    """Linea de un pais: nombre — estado — hace cuanto — evidencia corta."""
    if snapshot is None or not snapshot.actualizado_en:
        return f"{pais.nombre} — {ETIQUETA_SIN_DATOS}"
    partes = [
        pais.nombre,
        ETIQUETAS.get(snapshot.estado, ETIQUETAS["desconocido"]),
        hace_cuanto(snapshot.actualizado_en, ahora),
    ]
    cita = cita_corta(snapshot.texto)
    if cita:
        partes.append(f"«{cita}»")
    return " — ".join(partes)


def tabla_estado(
    paises: dict[str, CountryConfig],
    estado: dict[str, Snapshot],
    ahora: datetime,
) -> str:
    """Tabla completa: una linea por pais, en el orden del TOML."""
    return "\n".join(
        linea_pais(pais, estado.get(codigo), ahora) for codigo, pais in paises.items()
    )


def main(
    ruta_config: Path = RUTA_CONFIG_DEFECTO,
    ruta_estado: Path = RUTA_DEFECTO,
    ahora: datetime | None = None,
) -> int:
    """CLI de solo lectura: imprime la tabla y termina (sin red ni Discord)."""
    try:  # banderas y «» en la consola de Windows (cp1252)
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # stdout capturado (tests) u otro limite
        pass
    paises = load_countries(ruta_config)
    estado = cargar(ruta_estado)
    print(tabla_estado(paises, estado, ahora or datetime.now(UTC)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
