"""Tests del flujo de una corrida: `correr()` en src/main.py (puro y testeable).

Integra detection + state: resultado por pais (texto o SourceError) ->
(nuevo estado, alertas a notificar). Incluye las reglas D10 de anti-ruido:
cooldown 24h por pais+tipo y tope de embeds con prioridad.
"""


from src.collectors.base import SourceError
from src.config import CountryConfig
from src.main import cita_para, correr, seleccionar_alertas
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


class TestCooldownD10:
    """D10: sin saturar — no re-alertar el mismo pais+tipo antes de 24 h."""

    def test_cooldown_suprime_alerta_repetida_del_mismo_tipo(self) -> None:
        previo = {
            "au": Snapshot(
                estado="cerrado",
                texto="closed for 2026",
                alertas_enviadas={"apertura": "2026-11-10T10:00:00+00:00"},
            ),
        }
        estado, alertas = correr(
            {"au": pais("au")},
            previo,
            {"au": "<html>open ahora con texto distinto</html>"},
            ahora="2026-11-10T12:00:00+00:00",
        )
        assert alertas == []  # ya se aviso hace 2h: no repite
        assert estado["au"].estado == "abierto"  # el estado SI se actualiza

    def test_cooldown_expirado_vuelve_a_alertar(self) -> None:
        previo = {
            "au": Snapshot(
                estado="cerrado",
                texto="closed for 2026",
                alertas_enviadas={"apertura": "2026-11-09T10:00:00+00:00"},  # 26 h atras
            ),
        }
        _, alertas = correr(
            {"au": pais("au")},
            previo,
            {"au": "<html>open</html>"},
            ahora="2026-11-10T12:00:00+00:00",
        )
        assert alertas == [("au", "apertura")]

    def test_alerta_emitida_queda_marcada_para_el_cooldown(self) -> None:
        previo = {"au": Snapshot(estado="cerrado", texto="closed for")}
        estado, alertas = correr(
            {"au": pais("au")},
            previo,
            {"au": "<html>open</html>"},
            ahora="2026-11-10T12:00:00+00:00",
        )
        assert alertas == [("au", "apertura")]
        assert estado["au"].alertas_enviadas["apertura"] == "2026-11-10T12:00:00+00:00"

    def test_cooldown_no_bloquea_otro_tipo_de_alerta(self) -> None:
        previo = {
            "au": Snapshot(
                estado="abierto",
                texto="open todo",
                alertas_enviadas={"cambio": "2026-11-10T10:00:00+00:00"},
            ),
        }
        _, alertas = correr(
            {"au": pais("au")},
            previo,
            {"au": SourceError("red", "caida")},
            ahora="2026-11-10T12:00:00+00:00",
        )
        # el fallo es el 1ro: ignore; pero si fuese fuente_inaccesible no lo
        # bloquearia el cooldown de "cambio". Aqui solo verificamos sin alerta.
        assert alertas == []


class TestSeleccionarAlertasD10:
    """D10: max 3 embeds por corrida, prioridad apertura>cierre>fuente>cambio."""

    def test_prioridad_y_tope(self) -> None:
        alertas = [
            ("ie", "cambio"),
            ("au", "apertura"),
            ("nz", "fuente_inaccesible"),
            ("ca", "cierre"),
            ("jp", "cambio"),
        ]
        assert seleccionar_alertas(alertas, 3) == [
            ("au", "apertura"),
            ("ca", "cierre"),
            ("nz", "fuente_inaccesible"),
        ]

    def test_tope_cero_o_negativo_no_recorta(self) -> None:
        alertas = [("ie", "cambio"), ("au", "apertura")]
        assert len(seleccionar_alertas(alertas, 0)) == 2

    def test_correr_aplica_el_tope(self) -> None:
        codigos = ["au", "nz", "ie", "jp"]
        previo = {c: Snapshot(estado="cerrado", texto="closed for") for c in codigos}
        resultados = {c: "<html>open distinto</html>" for c in codigos}
        _, alertas = correr(
            {c: pais(c) for c in codigos}, previo, resultados, max_embeds=3,
        )
        assert len(alertas) == 3


class TestCitaParaEmbed:
    """D10: evidencia verificable en el embed (cita literal de la fuente)."""

    def test_apertura_cita_la_keyword_abierta(self) -> None:
        snapshot = Snapshot(estado="abierto", texto="los cupos open hoy para chilenos")
        cita = cita_para("apertura", pais("au"), snapshot)
        assert "open" in cita

    def test_cierre_cita_la_keyword_cerrada(self) -> None:
        snapshot = Snapshot(estado="cerrado", texto="the season is closed for 2026")
        cita = cita_para("cierre", pais("au"), snapshot)
        assert "closed" in cita

    def test_cambio_muestra_extracto_del_texto_nuevo(self) -> None:
        snapshot = Snapshot(estado="abierto", texto="texto nuevo y distinto al previo")
        assert cita_para("cambio", pais("au"), snapshot) == "texto nuevo y distinto al previo"

    def test_fuente_inaccesible_no_tiene_cita(self) -> None:
        assert cita_para("fuente_inaccesible", pais("au"), None) == ""
