"""Simulador de Discord: prueba el flujo completo SIN credenciales reales.

Levanta un servidor HTTP local que hace de webhook de Discord, apunta las
variables DISCORD_WEBHOOK_* hacia el, fabrica un estado previo que provoca
una APERTURA (canal publico) y un CAMBIO (canal admin), corre el bot real
contra las fuentes oficiales y muestra los payloads capturados.

Credenciales reales: cero. Ideal para verificar el ruteo D9, la evidencia
D10 y la ausencia de menciones sin exponer webhooks.

Modo opcional `--reenviar`: ademas de capturar, reenvia cada payload a los
webhooks REALES que tu mismo tengas en las variables de entorno (solo en tu
PC, nunca en el chat del agente) — para ver los embeds reales en tu Discord
de pruebas.

Uso (desde la raiz del repo):
  python tools/simular_discord.py              # solo simulacion local
  python tools/simular_discord.py --reenviar   # + embeds reales en tu Discord
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PUERTO = 8765
RECIBIDOS: list[dict] = []
WEBHOOK_POR_CANAL = {  # canal simulado -> variable de entorno real
    "canal-publico": "DISCORD_WEBHOOK_URL",
    "canal-admin": "DISCORD_WEBHOOK_ADMIN_URL",
}


class Receptor(BaseHTTPRequestHandler):
    """Hace de webhook de Discord: responde 204 y guarda el payload."""

    def do_POST(self) -> None:  # noqa: N802 — nombre fijado por http.server
        largo = int(self.headers.get("Content-Length", 0))
        RECIBIDOS.append(
            {
                "canal": self.path.lstrip("/"),
                "payload": json.loads(self.rfile.read(largo)),
            }
        )
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args) -> None:  # silencio en consola
        pass


# Estado previo fabricado para provocar las 2 alertas que viajan por canales
# distintos (D9): JP "cerrado" con fuente real abierta -> APERTURA (publico);
# CA con texto distinto y mismo estado -> CAMBIO (admin).
ESTADO_PROVOCADOR = {
    "jp": {"estado": "cerrado", "texto": "estado viejo sin agendamiento"},
    "ca": {"estado": "cerrado", "texto": "texto viejo del snapshot anterior"},
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    servidor = HTTPServer(("127.0.0.1", PUERTO), Receptor)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()

    ruta_estado = Path("data/state.json")
    respaldo = ruta_estado.read_text(encoding="utf-8") if ruta_estado.exists() else None
    ruta_estado.write_text(json.dumps(ESTADO_PROVOCADOR), encoding="utf-8")
    try:
        entorno = os.environ | {
            "DISCORD_WEBHOOK_URL": f"http://127.0.0.1:{PUERTO}/canal-publico",
            "DISCORD_WEBHOOK_ADMIN_URL": f"http://127.0.0.1:{PUERTO}/canal-admin",
            "PYTHONIOENCODING": "utf-8",
        }
        resultado = subprocess.run(
            [sys.executable, "-m", "src.main"],
            env=entorno,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print("--- salida del bot ---")
        print(resultado.stdout.strip() or "(sin salida)")
    finally:
        # el estado real del repo se restaura: la simulacion no contamina
        if respaldo is not None:
            ruta_estado.write_text(respaldo, encoding="utf-8")
        servidor.shutdown()

    print(f"\n--- {len(RECIBIDOS)} payloads capturados por el simulador ---")
    for recibido in RECIBIDOS:
        embed = recibido["payload"]["embeds"][0]
        print(f"\n[canal {recibido['canal']}]")
        print(f"  titulo: {embed['title']}")
        print(f"  color:  #{embed['color']:06x}")
        print(f"  url:    {embed['url'][:70]}")
        print(f"  allowed_mentions: {recibido['payload'].get('allowed_mentions')}")
        print(f"  footer: {embed['footer']['text']}")
        for campo in embed.get("fields", []):
            print(f"  campo [{campo['name']}]: {campo['value'][:130]}")

    if "--reenviar" in sys.argv:
        reenviar_a_discord()
    return 0


def reenviar_a_discord() -> None:
    """Reenvia los payloads capturados a tus webhooks reales (solo tu PC)."""
    import httpx

    for recibido in RECIBIDOS:
        variable = WEBHOOK_POR_CANAL.get(recibido["canal"], "")
        destino = os.environ.get(variable, "")
        if not destino:
            print(f"\n[{recibido['canal']}] sin webhook real en ${variable}: no reenviado")
            continue
        with httpx.Client() as client:
            respuesta = client.post(destino, json=recibido["payload"], timeout=15.0)
        ok = 200 <= respuesta.status_code < 300
        print(f"\n[{recibido['canal']}] reenviado a ${variable}: {'OK' if ok else f'HTTP {respuesta.status_code}'}")


if __name__ == "__main__":
    sys.exit(main())
