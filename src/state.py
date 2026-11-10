"""Persistencia del estado: snapshots por pais en data/state.json.

El archivo se commitea al repo (decision D3) y GitHub Actions lo actualiza en
cada corrida. La carga es tolerante: archivo ausente o corrupto = estado vacio
-> la corrida siguiente hace siembra silenciosa (docs/PLAN.md R1).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

RUTA_DEFECTO = Path("data/state.json")


@dataclass(frozen=True)
class Snapshot:
    """Ultimo estado conocido de un pais."""

    estado: str  # "abierto" | "cerrado" | "desconocido"
    texto: str  # texto extraido de la fuente (para detectar cambios)
    fallas_consecutivas: int = 0  # contador para la regla R3
    actualizado_en: str = ""  # ISO UTC de la ultima actualizacion


def cargar(ruta: Path = RUTA_DEFECTO) -> dict[str, Snapshot]:
    if not ruta.exists():
        return {}
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {codigo: Snapshot(**crudo) for codigo, crudo in datos.items()}


def guardar(estado: dict[str, Snapshot], ruta: Path = RUTA_DEFECTO) -> None:
    ruta.write_text(
        json.dumps({codigo: asdict(snapshot) for codigo, snapshot in estado.items()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
