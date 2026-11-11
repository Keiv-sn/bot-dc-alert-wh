"""Tests de config: carga countries.toml -> dataclasses validadas."""

from pathlib import Path

import pytest

from src.config import ConfigError, load_alertas_config, load_countries

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

    def test_acceso_navegador_solo_para_fuentes_con_waf(self) -> None:
        paises = load_countries(CONFIG_REAL)
        assert paises["au"].acceso == "http"
        assert paises["ca"].acceso == "navegador"
        assert paises["nz"].acceso == "navegador"
        assert paises["jp"].acceso == "navegador"

    def test_acceso_desconocido_da_error_claro(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[paises.xx]\nnombre = "X"\nurl = "https://x"\nmetodo = "texto"\n'
            'acceso = "homing-pigeon"\nkeywords_abierto = []\nkeywords_cerrado = []\n',
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="homing-pigeon"):
            load_countries(config)

    def test_metodo_valido_y_datos_asociados(self) -> None:
        for pais in load_countries(CONFIG_REAL).values():
            if pais.metodo == "fila":
                assert pais.ancla
            elif pais.metodo == "selector":
                assert pais.selector

    def test_contexto_antinoticia_solo_donde_aplica(self) -> None:
        paises = load_countries(CONFIG_REAL)
        assert paises["ie"].contexto == "chile"  # texto completo: exige contexto
        assert paises["au"].contexto == ""  # fila anclada: ya esta acotada

    def test_selector_seccion_para_textos_enormes(self) -> None:
        paises = load_countries(CONFIG_REAL)
        assert paises["ca"].selector_seccion == "main"  # sin menus -> menos CAMBIO
        assert paises["ie"].selector_seccion == "main"
        assert paises["au"].selector_seccion == ""


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


class TestConfigAlertasD10:
    """Seccion [alertas] opcional: cooldown y tope de embeds (PLAN D10)."""

    def test_seccion_ausente_usa_defaults_comunidad(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[paises.au]\nnombre = "A"\nurl = "https://x"\nmetodo = "texto"\n',
            encoding="utf-8",
        )
        alertas = load_alertas_config(config)
        assert alertas.cooldown_horas == 24
        assert alertas.max_embeds_corrida == 3

    def test_seccion_con_valores_custom(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            "[alertas]\ncooldown_horas = 6\nmax_embeds_corrida = 5\n"
            '[paises.au]\nnombre = "A"\nurl = "https://x"\nmetodo = "texto"\n',
            encoding="utf-8",
        )
        alertas = load_alertas_config(config)
        assert alertas.cooldown_horas == 6
        assert alertas.max_embeds_corrida == 5

    def test_clave_desconocida_da_error_claro(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[alertas]\ncooldown_horasss = 24\n[paises.au]\nnombre = "A"\n'
            'url = "https://x"\nmetodo = "texto"\n',
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="cooldown_horasss"):
            load_alertas_config(config)

    def test_valor_no_entero_da_error_claro(self, tmp_path: Path) -> None:
        config = tmp_path / "countries.toml"
        config.write_text(
            '[alertas]\ncooldown_horas = "veinticuatro"\n[paises.au]\nnombre = "A"\n'
            'url = "https://x"\nmetodo = "texto"\n',
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="cooldown_horas"):
            load_alertas_config(config)

    def test_config_real_tiene_seccion_alertas(self) -> None:
        alertas = load_alertas_config(CONFIG_REAL)
        assert alertas.cooldown_horas == 24
        assert alertas.max_embeds_corrida == 3
