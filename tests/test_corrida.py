"""Tests del flujo de una corrida: `correr()` en src/main.py (puro y testeable).

Integra detection + state: resultado por pais (texto o SourceError) ->
(nuevo estado, alertas a notificar).
"""


from src.collectors.base import SourceError
from src.config import CountryConfig
from src.main import correr
from src.state import Snapshot


def pais(codigo: str) -> CountryConfig:
    return CountryConfig(
        codigo=codigo,
        nombre=codigo,
        url="https://ejemplo",
        metodo="texto",
        keywords_abierto=["open"],
        keywords_cerrado=["closed for"],
    )


def test_primera_corrida_es_siembra_silenciosa() -> None:
    estado, alertas = correr(
        {"au": pais("au")},
        estado_previo={},
        resultados={"au": "<html>open</html>"},
    )
    assert alertas == []
    assert estado["au"].estado == "abierto"
    assert estado["au"].fallas_consecutivas == 0


def test_cerrado_a_abierto_genera_alerta_apertura() -> None:
    previo = {"au": Snapshot(estado="cerrado", texto="closed for 2026")}
    estado, alertas = correr(
        {"au": pais("au")},
        estado_previo=previo,
        resultados={"au": "<html>open</html>"},
    )
    assert alertas == [("au", "apertura")]
    assert estado["au"].estado == "abierto"


def test_sin_cambios_no_alerta_ni_cambia_snapshot_de_texto() -> None:
    previo = {"au": Snapshot(estado="abierto", texto="open")}
    estado, alertas = correr({"au": pais("au")}, previo, {"au": "open"})
    assert alertas == []
    assert estado["au"].texto == "open"


def test_primer_fallo_se_ignora_y_marca_contador() -> None:
    previo = {"au": Snapshot(estado="abierto", texto="open")}
    estado, alertas = correr(
        {"au": pais("au")},
        previo,
        {"au": SourceError("red", "simulado")},
    )
    assert alertas == []
    assert estado["au"].fallas_consecutivas == 1
    assert estado["au"].estado == "abierto"  # no toca lo ultimo sabido


def test_segundo_fallo_consecutivo_notifica_y_resetea_contador() -> None:
    previo = {"au": Snapshot(estado="abierto", texto="open", fallas_consecutivas=1)}
    estado, alertas = correr(
        {"au": pais("au")},
        previo,
        {"au": SourceError("http_status", "403 simulado")},
    )
    assert alertas == [("au", "fuente_inaccesible")]
    assert estado["au"].fallas_consecutivas == 0
    assert estado["au"].texto == "open"


def test_fallo_no_bloquea_los_demas_paises() -> None:
    previo = {
        "au": Snapshot(estado="cerrado", texto="closed for"),
        "nz": Snapshot(estado="cerrado", texto="closed for 2026"),
    }
    estado, alertas = correr(
        {"au": pais("au"), "nz": pais("nz")},
        previo,
        {
            "au": SourceError("red", "caida simulada"),
            "nz": "<html>open for 2026</html>",
        },
    )
    codigos_alertados = [codigo for codigo, _ in alertas]
    assert codigos_alertados == ["nz"]  # au fallo, nz abrio y alerta igual
    assert estado["nz"].estado == "abierto"


def test_fallo_en_primera_corrida_queda_contado_para_la_siguiente() -> None:
    estado, alertas = correr(
        {"au": pais("au")},
        estado_previo={},
        resultados={"au": SourceError("red", "simulado")},
    )
    assert alertas == []
    assert estado["au"].fallas_consecutivas == 1
    assert estado["au"].estado == "desconocido"


def test_estampas_de_tiempo_se_respetan(tmp_path=None) -> None:
    estado, _ = correr(
        {"au": pais("au")},
        estado_previo={},
        resultados={"au": "<html>open</html>"},
        ahora="2026-11-10T12:00:00+00:00",
    )
    assert estado["au"].actualizado_en == "2026-11-10T12:00:00+00:00"
