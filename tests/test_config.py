"""Tests de config: carga countries.toml -> dataclasses validadas."""

from pathlib import Path

import pytest

from src.config import ConfigError, load_countries

CONFIG_REAL = Path("config/countries.toml")
CODIGOS_ESPERADOS = {"au", "ca", "ie", "nz", "jp"}


class TestConfigReal:
    def test_carga_los_cinco_paises(self) -> None:
        paises = load_countries(CONFIG_REAL)
        assert set(paises) == CODIGOS_ESPERADOS

    def test_cada_pais_tiene_url_oficial(self) -> None:
        for pais in load_countries(CONFIG_REAL).values():
            assert pais.url.startswith("https://")
            assert pais.nombre

    def test_canada_tiene_keywords_de_temporada_verificados(self) -> None:
        ca = load_countries(CONFIG_REAL)["ca"]
        assert "season is open" in ca.keywords_abierto
        assert "season is closed" in ca.keywords_cerrado

    def test_metodo_valido_y_datos_asociados(self) -> None:
        for pais in load_countries(CONFIG_REAL).values():
            if pais.metodo == "fila":
                assert pais.ancla
            elif pais.metodo == "selector":
                assert pais.selector


class TestValidaciones:
    def test_archivo_inexistente_da_error_claro(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="no-existe.toml"):
            load_countries(tmp_path / "no-existe.toml")

    def test_pais_sin_campo_obligatorio_da_error_claro(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[paises.au]\nnombre = "Australia"\nmetodo = "texto"\n',
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match=r"\[paises\.au\].*url"):
            load_countries(config)

    def test_metodo_fila_exige_ancla(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[paises.au]\nnombre = "A"\nurl = "https://x"\nmetodo = "fila"\n'
            'keywords_abierto = []\nkeywords_cerrado = []\n',
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="ancla"):
            load_countries(config)

    def test_metodo_selector_exige_selector(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[paises.nz]\nnombre = "N"\nurl = "https://x"\nmetodo = "selector"\n'
            'keywords_abierto = []\nkeywords_cerrado = []\n',
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="selector"):
            load_countries(config)

    def test_metodo_desconocido_da_error_claro(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[paises.xx]\nnombre = "X"\nurl = "https://x"\nmetodo = "magia"\n'
            'keywords_abierto = []\nkeywords_cerrado = []\n',
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="magia"):
            load_countries(config)
