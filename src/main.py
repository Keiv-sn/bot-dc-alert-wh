"""Orquestador del bot: colectar → detectar → notificar → guardar.

Etapa 1: esqueleto mínimo. Las etapas 2-5 del ROADMAP reemplazan este
marcador por el flujo real, etapa por etapa siguiendo TDD.
"""

import sys


def main() -> int:
    """Punto de entrada único del bot. Debe terminar SIEMPRE con exit 0:
    una corrida fallida (fuente caída, webhook caído) no debe romper el
    build de GitHub Actions, porque el monitoreo de los demás países debe
    vivir de  a  continuar (ver docs/PLAN.md §7, reglas R3 y R4).
    """
    print("ok: esqueleto de Etapa 1 listo — flujo real llega en Etapa 2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
