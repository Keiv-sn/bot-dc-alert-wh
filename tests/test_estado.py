"""Tests del renderizador de estado compartido y del CLI de terminal.

El renderizador es UNA sola fuente de verdad: alimenta el CLI
`python -m src.estado` (opcion A, solo lectura) y el embed del digest
diario al canal admin (opcion C). Puro: sin red ni Discord.
"""

from datetime import UTC, datetime
from pathlib import Path

from src.config import CountryConfig, load_countries
from src.estado import (
    LARGO_CITA,
    cita_corta,
    hace_cuanto,
    linea_pais,
    main,
    tabla_estado,
)
from src.state import Snapshot, guardar

CONFIG_REAL = Path("config/countries.toml")
AHORA = datetime(2026, 11, 15, 12, 0, tzinfo=UTC)


def pais(codigo: str = "au", nombre: str = "Australia 🇦🇺") -> CountryConfig:
    return CountryConfig(
        codigo=codigo, nombre=nombre, url="https://fuente/oficial", metodo="texto",
    )


class TestHaceCuanto:
    def test_horas_transcurridas(self) -> None:
        anterior = "2026-11-15T09:00:00+00:00"
        assert hace_cuanto(anterior, AHORA) == "hace 3 h"

    def test_menos_de_una_hora(self) -> None:
        anterior = "2026-11-15T11:20:00+00:00"
        assert hace_cuanto(anterior, AHORA) == "hace menos de 1 h"

    def test_mas_de_dos_dias_se_muestra_en_dias(self) -> None:
        anterior = "2026-11-12T06:00:00+00:00"  # 78 h antes
        assert hace_cuanto(anterior, AHORA) == "hace 3 d"

    def test_sin_dato_devuelve_sin_datos(self) -> None:
        assert hace_cuanto("", AHORA) == "sin datos"

    def test_iso_invalido_devuelve_sin_datos(self) -> None:
        assert hace_cuanto("no-es-fecha", AHORA) == "sin datos"

    def test_timestamp_futuro_no_da_horas_negativas(self) -> None:
        futuro = "2026-11-15T15:00:00+00:00"
        assert hace_cuanto(futuro, AHORA) == "hace menos de 1 h"


class TestCitaCorta:
    def test_colapsa_espacios_y_saltos(self) -> None:
        assert cita_corta("a\n  b\t  c") == "a b c"

    def test_recorta_con_elipsis(self) -> None:
        cita = cita_corta("x" * 200)
        assert len(cita) == LARGO_CITA + 1  # + elipsis
        assert cita.endswith("…")

    def test_cita_justa_no_lleva_elipsis(self) -> None:
        texto = "y" * LARGO_CITA
        assert cita_corta(texto) == texto

    def test_texto_vacio_devuelve_vacio(self) -> None:
        assert cita_corta("   \n  ") == ""


class TestLineaPais:
    def test_pais_abierto_con_datos(self) -> None:
        snapshot = Snapshot(
            estado="abierto",
            texto="Chile Open 3,400 places",
            actualizado_en="2026-11-15T10:00:00+00:00",
        )
        linea = linea_pais(pais(), snapshot, AHORA)
        assert linea == "Australia 🇦🇺 — 🟢 ABIERTO — hace 2 h — «Chile Open 3,400 places»"

    def test_pais_cerrado(self) -> None:
        snapshot = Snapshot(
            estado="cerrado", texto="closed", actualizado_en="2026-11-15T11:00:00+00:00",
        )
        linea = linea_pais(pais(), snapshot, AHORA)
        assert "🔴 CERRADO" in linea
        assert "hace 1 h" in linea

    def test_estado_desconocido(self) -> None:
        snapshot = Snapshot(
            estado="desconocido", texto="txt", actualizado_en="2026-11-15T11:00:00+00:00",
        )
        assert "⚪ DESCONOCIDO" in linea_pais(pais(), snapshot, AHORA)

    def test_sin_snapshot_da_sin_datos(self) -> None:
        assert linea_pais(pais(), None, AHORA) == "Australia 🇦🇺 — ⚪ SIN DATOS"

    def test_snapshot_sin_actualizado_en_da_sin_datos(self) -> None:
        snapshot = Snapshot(estado="abierto", texto="x")
        assert "SIN DATOS" in linea_pais(pais(), snapshot, AHORA)


class TestTablaEstado:
    def test_una_linea_por_pais_en_el_orden_del_toml(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[paises.zz]\nnombre = "Zeta"\nurl = "https://z"\nmetodo = "texto"\n'
            '[paises.aa]\nnombre = "Alfa"\nurl = "https://a"\nmetodo = "texto"\n',
            encoding="utf-8",
        )
        tabla = tabla_estado(load_countries(config), {}, AHORA)
        # orden del TOML (no alfabetico) y paises sin datos en el estado
        assert tabla.splitlines() == ["Zeta — ⚪ SIN DATOS", "Alfa — ⚪ SIN DATOS"]

    def test_config_real_genera_13_lineas(self) -> None:
        paises = load_countries(CONFIG_REAL)
        assert len(tabla_estado(paises, {}, AHORA).splitlines()) == 13


class TestCliEstado:
    """Opcion A: `python -m src.estado` — solo lectura, sin red ni Discord."""

    def _escenario(self, tmp_path: Path) -> tuple[Path, Path]:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[paises.au]\nnombre = "Australia 🇦🇺"\nurl = "https://au"\n'
            'metodo = "texto"\nkeywords_abierto = ["open"]\n'
            'keywords_cerrado = ["closed"]\n'
            '[paises.fr]\nnombre = "Francia 🇫🇷"\nurl = "https://fr"\nmetodo = "texto"\n',
            encoding="utf-8",
        )
        estado = tmp_path / "state.json"
        snapshot = Snapshot(
            estado="abierto", texto="Open now",
            actualizado_en="2026-11-15T10:00:00+00:00",
        )
        guardar({"au": snapshot}, ruta=estado)
        return config, estado

    def test_imprime_tabla_y_termina_en_cero(self, tmp_path: Path, capsys) -> None:
        config, estado = self._escenario(tmp_path)

        codigo = main(ruta_config=config, ruta_estado=estado, ahora=AHORA)
        salida = capsys.readouterr().out

        assert codigo == 0
        assert "Australia 🇦🇺 — 🟢 ABIERTO" in salida
        assert "Francia 🇫🇷 — ⚪ SIN DATOS" in salida

    def test_lee_formato_viejo_de_state_json(self, tmp_path: Path, capsys) -> None:
        config, _ = self._escenario(tmp_path)
        estado = tmp_path / "state-viejo.json"
        estado.write_text(
            '{"au": {"estado": "cerrado", "texto": "Closed", '
            '"fallas_consecutivas": 0, "actualizado_en": "2026-11-15T10:00:00+00:00"}}',
            encoding="utf-8",
        )

        assert main(ruta_config=config, ruta_estado=estado, ahora=AHORA) == 0
        assert "🔴 CERRADO" in capsys.readouterr().out
