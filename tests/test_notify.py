"""Tests de notificaciones Discord: payload por tipo + envio tolerante."""


import httpx
import pytest

from src.config import CountryConfig
from src.notify import construir_mensaje, enviar, hora_chile


def pais() -> CountryConfig:
    return CountryConfig(
        codigo="au",
        nombre="Australia 🇦🇺",
        url="https://fuente/oficial",
        metodo="texto",
    )


class TestConstruirMensaje:
    CASOS = {
        "apertura": (["🟢", "abierta"], 0x57F287),
        "cierre": (["🔴", "cerr"], 0xED4245),
        "cambio": (["🔄", "cambi"], 0xFEE75C),
        "fuente_inaccesible": (["⚠️", "fuente"], 0x99AAB5),
    }

    @pytest.mark.parametrize("tipo", list(CASOS))
    def test_embed_con_color_titulo_titulo_url(self, tipo: str) -> None:
        (frases, color) = self.CASOS[tipo]
        payload = construir_mensaje(pais(), tipo, detalle="antes: cerrado")

        embed = payload["embeds"][0]
        assert embed["color"] == color
        assert embed["url"] == pais().url
        assert f"{pais().nombre}" in embed["title"]
        assert frases[0] in embed["title"]
        for frase in frases:
            assert frase in embed["description"].lower() or frase in embed["title"]

    def test_apertura_incluye_estado_anterior(self) -> None:
        embed = construir_mensaje(pais(), "apertura", detalle="antes: cerrado")["embeds"][0]
        assert "cerrado" in embed["description"]


class TestHoraChile:
    def test_utc_a_hora_de_santiago(self) -> None:
        # 12:00 UTC = 09:00 CLT en noviembre (horario de verano)
        mensaje = hora_chile("2026-11-10T12:00:00+00:00")
        assert "09:00" in mensaje
        assert "10-11" in mensaje or "10/11" in mensaje or "10 nov" in mensaje.lower()

    def test_timestamp_invalido_no_explota(self) -> None:
        assert hora_chile("no-es-fecha") == ""


class TestEnviar:
    WEBHOOK = "https://discord.com/api/webhooks/123/abc"

    def test_post_200_devuelve_true(self) -> None:
        cuerpo: list[bytes] = []

        def handler(request: httpx.Request) -> httpx.Response:
            cuerpo.append(request.content)
            return httpx.Response(200)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            assert enviar(self.WEBHOOK, {"embeds": [{"title": "hola"}]}, client) is True
        assert b"embeds" in cuerpo[0]

    def test_error_de_discord_reintenta_una_vez_y_devuelve_false(self) -> None:
        llamadas = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal llamadas
            llamadas += 1
            return httpx.Response(500)

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            resultado = enviar(self.WEBHOOK, {"embeds": []}, client)
        assert llamadas == 2  # 1 intento + 1 reintento
        assert resultado is False

    def test_red_caida_devuelve_false_sin_explotar(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("caido")

        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            assert enviar(self.WEBHOOK, {"embeds": []}, client) is False
