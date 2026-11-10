"""Carga y validacion de config/countries.toml.

Todo el conocimiento volatil del bot (URLs y keywords) vive en el TOML, no en
el codigo: agregar un pais es agregar un bloque, cero codigo nuevo (docs/PLAN.md
§6, principio 4).
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RUTA_CONFIG_DEFECTO = Path("config/countries.toml")

METODOS_VALIDOS = {"texto", "fila", "selector"}
ACCESOS_VALIDOS = {"http", "navegador"}
ACCESO_DEFECTO = "http"


class ConfigError(Exception):
    """Configuracion ausente, incompleta o invalida; nunca se ignora en silencio."""


@dataclass(frozen=True)
class CountryConfig:
    """Config de un pais monitoreado."""

    codigo: str
    nombre: str
    url: str
    metodo: str
    keywords_abierto: list[str] = field(default_factory=list)
    keywords_cerrado: list[str] = field(default_factory=list)
    acceso: str = ACCESO_DEFECTO
    url_respaldo: str = ""
    ancla: str = ""
    selector: str = ""


def load_countries(ruta: Path = RUTA_CONFIG_DEFECTO) -> dict[str, CountryConfig]:
    """Lee el TOML y devuelve {codigo: CountryConfig}, con errores claros."""
    if not ruta.exists():
        raise ConfigError(f"No existe el archivo de configuracion: {ruta}")
    datos = tomllib.loads(ruta.read_text(encoding="utf-8"))
    paises_crudos = datos.get("paises")
    if not isinstance(paises_crudos, dict) or not paises_crudos:
        raise ConfigError(f"{ruta} no define la seccion [paises.X]")

    return {
        codigo: _a_country_config(codigo, datos_pais, ruta)
        for codigo, datos_pais in paises_crudos.items()
    }


def _a_country_config(codigo: str, datos: dict, ruta: Path) -> CountryConfig:
    def error_claro(estuvo_mal: str) -> ConfigError:
        return ConfigError(f"[paises.{codigo}] de {ruta}: {estuvo_mal}")

    for campo in ("nombre", "url", "metodo"):
        if not str(datos.get(campo, "")).strip():
            raise error_claro(f"falta el campo obligatorio '{campo}'")

    metodo = str(datos["metodo"])
    if metodo not in METODOS_VALIDOS:
        raise error_claro(
            f"metodo '{metodo}' desconocido; validos: {sorted(METODOS_VALIDOS)}"
        )
    if metodo == "fila" and not str(datos.get("ancla", "")).strip():
        raise error_claro("metodo 'fila' exige el campo 'ancla'")
    if metodo == "selector" and not str(datos.get("selector", "")).strip():
        raise error_claro("metodo 'selector' exige el campo 'selector'")

    acceso = str(datos.get("acceso", ACCESO_DEFECTO))
    if acceso not in ACCESOS_VALIDOS:
        raise error_claro(
            f"acceso '{acceso}' desconocido; validos: {sorted(ACCESOS_VALIDOS)}"
        )

    return CountryConfig(
        codigo=codigo,
        nombre=str(datos["nombre"]),
        url=str(datos["url"]),
        metodo=metodo,
        keywords_abierto=list(datos.get("keywords_abierto", [])),
        keywords_cerrado=list(datos.get("keywords_cerrado", [])),
        acceso=acceso,
        url_respaldo=str(datos.get("url_respaldo", "")),
        ancla=str(datos.get("ancla", "")),
        selector=str(datos.get("selector", "")),
    )
