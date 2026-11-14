# Bot de Alertas Working Holiday Chile 🇨🇱

Bot en Python que monitorea las páginas oficiales de los programas **Working Holiday**
disponibles para ciudadanos chilenos en trece países — Australia 🇦🇺, Canadá 🇨🇦,
Irlanda 🇮🇪, Nueva Zelanda 🇳🇿, Japón 🇯🇵, Alemania 🇩🇪, Francia 🇫🇷, Corea del Sur 🇰🇷,
Dinamarca 🇩🇰, Suecia 🇸🇪, Portugal 🇵🇹, Islandia 🇮🇸 y Suiza 🇨🇭 — y avisa por
**Discord** cuando una convocatoria abre, cierra o cambia. Corre cada 4 horas en
GitHub Actions, sin necesidad de PC encendida.

## Documentación del proyecto

La documentación interna del proyecto (plan, roadmap y bitácora de sesiones)
**no es pública**: vive solo en el disco de trabajo (`docs/` está excluido del
repositorio por decisión del autor) y no se sube a GitHub.

> **Para agentes de IA (en la máquina del autor):** leer los 3 documentos en
> `docs/` antes de escribir código, respetar las decisiones D1–D10 y registrar
> la sesión al final en `docs/BITACORA.md`.

## Estructura

```
bot-dc-wh/
├── src/
│   ├── main.py          # orquestador: colectar → detectar → notificar → guardar
│   ├── config.py        # carga countries.toml → dataclasses
│   ├── collectors/      # extracción de cada fuente oficial
│   ├── detection.py     # comparación con estado previo → decisión
│   ├── notify.py        # embeds → webhook de Discord
│   └── state.py         # data/state.json
├── config/countries.toml
├── data/state.json      # estado persistente (commiteado — decisión D3)
└── tests/fixtures/      # HTML real de las fuentes (truth para tests)
```

## Uso local

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install httpx beautifulsoup4 "playwright>=1.49" tzdata pytest ruff
python -m playwright install chromium   # para los países con acceso "navegador"

python -m src.main      # corrida del bot
pytest                  # tests
ruff check .            # linter
```

## Canales de Discord (diseño para comunidad grande — PLAN §8)

| Alerta | Canal | Webhook (variable de entorno) |
|--------|-------|-------------------------------|
| 🟢 Apertura / 🔴 Cierre | público (comunidad) | `DISCORD_WEBHOOK_URL` |
| 🔄 Cambio / ⚠️ Fuente inaccesible | admin (staff) | `DISCORD_WEBHOOK_ADMIN_URL` |

Cada embed indica **"Detectado"** con hora de Chile, **nunca menciona a nadie**
(`allowed_mentions: []`), limita la alertas por corrida y respeta un cooldown
de 24 h por país. La apertura/cierre incluyen la **evidencia**: cita literal
de la fuente oficial más el enlace directo para verificar.

Si el canal admin no tiene webhook, esas alertas quedan solo en el log de la corrida.

## Principios

Código limpio, funciones pequeñas, type hints, config como datos
(`countries.toml`), TDD en toda la lógica, linter `ruff` en verde antes de cada commit.
