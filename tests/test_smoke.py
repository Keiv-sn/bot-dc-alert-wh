"""Test smoke de Etapa 1: verifica que la estructura del proyecto corazón late."""

from src.main import main


def test_esqueleto_corre_y_termina_ok() -> None:
    assert main() == 0
