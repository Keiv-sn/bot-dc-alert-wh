"""Test smoke: el flujo `correr()` late end-to-end (sin red, sin archivos)."""

from src.config import CountryConfig
from src.main import correr


def test_flujo_minimo_late() -> None:
    pais = CountryConfig(
        codigo="test", nombre="Test", url="https://x", metodo="texto",
        keywords_abierto=["open"],
    )
    estado, alertas = correr({"test": pais}, {}, {"test": "<html>open</html>"})
    assert alertas == []  # primera corrida: siembra silenciosa
    assert estado["test"].estado == "abierto"
