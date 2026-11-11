"""Tests de persistencia: data/state.json tolerante y completo (Etapa 3)."""

import json

import pytest

from src.state import Snapshot, cargar, guardar


def test_guardar_y_cargar_round_trip(tmp_path) -> None:
    snapshot = Snapshot(
        estado="abierto", texto="open", actualizado_en="2026-11-10T12:00:00+00:00",
    )
    estado = {"au": snapshot}
    destino = tmp_path / "state.json"

    guardar(estado, destino)
    cargado = cargar(destino)

    assert cargado == estado


def test_archivo_inexistente_da_estado_vacio(tmp_path) -> None:
    assert cargar(tmp_path / "no-existe.json") == {}


def test_archivo_corrupto_da_estado_vacio_sin_explotar(tmp_path) -> None:
    destino = tmp_path / "state.json"
    destino.write_text("{no-soy-json", encoding="utf-8")
    assert cargar(destino) == {}


def test_estructura_json_legible(tmp_path) -> None:
    destino = tmp_path / "state.json"
    guardar({"nz": Snapshot(estado="cerrado", texto="closed for 2026")}, destino)
    datos = json.loads(destino.read_text(encoding="utf-8"))
    assert datos["nz"]["estado"] == "cerrado"
    assert datos["nz"]["texto"] == "closed for 2026"
    assert datos["nz"]["fallas_consecutivas"] == 0


def test_snapshot_es_frozen(tmp_path) -> None:
    snapshot = Snapshot(estado="abierto", texto="x")
    with pytest.raises(Exception):  # noqa: B017 — dataclasses.FrozenInstanceError
        snapshot.estado = "cerrado"


class TestAlertasEnviadasD10:
    """Cooldown 24 h: marcas por tipo persistidas (docs/PLAN.md D10)."""

    def test_alertas_enviadas_round_trip(self, tmp_path) -> None:
        snapshot = Snapshot(
            estado="abierto",
            texto="open",
            alertas_enviadas={"apertura": "2026-11-10T12:00:00+00:00"},
        )
        destino = tmp_path / "state.json"

        guardar({"au": snapshot}, destino)

        assert cargar(destino) == {"au": snapshot}

    def test_estado_viejo_sin_alertas_enviadas_carga_tolerante(self, tmp_path) -> None:
        destino = tmp_path / "state.json"
        destino.write_text(
            '{"au": {"estado": "abierto", "texto": "open", '
            '"fallas_consecutivas": 0, "actualizado_en": "2026-11-10T12:00:00+00:00"}}',
            encoding="utf-8",
        )
        cargado = cargar(destino)
        assert cargado["au"].alertas_enviadas == {}
