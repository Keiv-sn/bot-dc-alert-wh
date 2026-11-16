"""Persistencia del estado: snapshots por pais en data/state.json.

El archivo se commitea al repo (decision D3) y GitHub Actions lo actualiza en
cada corrida. La carga es tolerante: archivo ausente o corrupto = estado vacio
-> la corrida siguiente hace siembra silenciosa (docs/PLAN.md R1).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

RUTA_DEFECTO = Path("data/state.json")
# Formato v2 del archivo: {"paises": {codigo: snapshot}, "digest_enviado_en": ISO}.
# El formato viejo (dict plano {codigo: snapshot}) sigue cargando tolerante.
CLAVE_PAISES = "paises"
CLAVE_DIGEST = "digest_enviado_en"


@dataclass(frozen=True)
class Snapshot:
    """Ultimo estado conocido de un pais."""

    estado: str  # "abierto" | "cerrado" | "desconocido"
    texto: str  # texto extraido de la fuente (para detectar cambios)
    fallas_consecutivas: int = 0  # contador para la regla R3
    actualizado_en: str = ""  # ISO UTC de la ultima actualizacion
    # D10 cooldown: ultima vez que se notifico cada tipo {tipo: ISO UTC}.
    # Estado viejo sin esta clave carga como {} (tolerante).
    alertas_enviadas: dict[str, str] = field(default_factory=dict)


def cargar(ruta: Path = RUTA_DEFECTO) -> dict[str, Snapshot]:
    """Snapshots por pais; formato viejo (plano) sigue siendo legible."""
    paises, _ = _leer(ruta)
    return paises


def cargar_digest(ruta: Path = RUTA_DEFECTO) -> str:
    """ISO UTC del ultimo digest enviado (opcion C); "" si nunca hubo."""
    _, digest = _leer(ruta)
    return digest


def _leer(ruta: Path) -> tuple[dict[str, Snapshot], str]:
    if not ruta.exists():
        return {}, ""
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}, ""
    if not isinstance(datos, dict):
        return {}, ""
    if CLAVE_PAISES in datos:  # formato v2
        crudos = datos.get(CLAVE_PAISES)
        digest = str(datos.get(CLAVE_DIGEST, "") or "")
    else:  # formato viejo: {codigo: snapshot} plano
        crudos = datos
        digest = ""
    if not isinstance(crudos, dict):
        return {}, ""
    paises: dict[str, Snapshot] = {}
    for codigo, crudo in crudos.items():
        try:
            paises[codigo] = Snapshot(**crudo)
        except (TypeError, ValueError):
            continue  # snapshot con claves raras se descarta (carga tolerante)
    return paises, digest


def guardar(
    estado: dict[str, Snapshot],
    ruta: Path = RUTA_DEFECTO,
    digest_enviado_en: str = "",
) -> None:
    """Escribe formato v2: snapshots por pais + ciclo del digest."""
    ruta.write_text(
        json.dumps(
            {
                CLAVE_PAISES: {codigo: asdict(s) for codigo, s in estado.items()},
                CLAVE_DIGEST: digest_enviado_en,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
