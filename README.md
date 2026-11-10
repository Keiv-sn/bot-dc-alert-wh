# Bot de Alertas Working Holiday Chile 🇨🇱

Bot en Python que monitorea las páginas oficiales de los programas **Working Holiday**
disponibles para ciudadanos chilenos en cinco países — Australia 🇦🇺, Canadá 🇨🇦,
Irlanda 🇮🇪, Nueva Zelanda 🇳🇿, Japón 🇯🇵 — y avisa por **Discord** cuando una
convocatoria abre, cierra o cambia. Corre cada 4 horas en GitHub Actions,
sin necesidad de PC encendida.

## Documentación del proyecto

| Archivo | Contenido |
|---------|-----------|
| [`docs/PLAN.md`](docs/PLAN.md) | Decisiones cerradas, arquitectura, fuentes oficiales, reglas de negocio, principios de código |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Hoja de ruta por etapas con criterios de cierre |
| [`docs/BITACORA.md`](docs/BITACORA.md) | Bitácora: todo agente registra hitos y hallazgos al final de cada sesión |

> **Para agentes de IA:** leer los 3 documentos antes de escribir código.
> Respetar las decisiones D1–D8 de `docs/PLAN.md` y registrar la sesión en `docs/BITACORA.md`.

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
├── tests/fixtures/      # HTML real de las fuentes (truth para tests)
└── docs/                # plan, roadmap y bitácora
```

## Uso local

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

python -m src.main      # corrida del bot
pytest                  # tests
ruff check .            # linter
```

## Principios (resumen — detalle en docs/PLAN.md §6)

Código limpio, funciones pequeñas, type hints, config como datos
(`countries.toml`), TDD en toda la lógica, linter `ruff` en verde antes de cada commit.
