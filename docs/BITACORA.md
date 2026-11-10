# BITÁCORA — Bot de Alertas Working Holiday Chile 🇨🇱

> **REGLA INQUEBRANTABLE:** cada agente (y cada sesión de trabajo) DEBE registrar al cierre una entrada en este archivo. Es la memoria viva del proyecto: hitos, hallazgos, pendientes, decisiones tomadas en el camino. Si no se registra, no pasó.
>
> **Formato — copiar la plantilla al final del archivo y completarla:**
>
> ```
> ------------------------------------------------------------
> ## YYYY-MM-DD | ETAPA N — [título corto]
> **Agente:** <nombre/ID del agente, ej. "opencode GLM-5.3-Flash-Free">
> **Que se hizo:**
> - <hito 1>
> - <hito 2>
> **Hallazgos renombrados:**
> - <descubrimientos útiles para el que viene: URLs, estructuras, bloqueos, decisiones>
> **Pendientes para la próxima sesión:**
> - <tarea 1>
> **Estado al cierre:** <etapa N completada: sí/no — qué falta>
> ```

---

## 2026-11-09 | FASE DE PLANIFICACIÓN — cierre de decisiones y documentos

**Agente:** opencode GLM-5.3-Flash-Free (sesión de planificación con Kevin)

**Qué se hizo:**
- Definición y cierre de las 8 decisiones centrales (D1–D8 en PLAN.md): 5 países (AU, CA, IE, NZ, JP), detección por keywords configurables, estado commiteado, Discord por webhook, cron 4h, TDD, clean code, stack mínimo
- Evaluación real de las 5 URLs oficiales propuestas por Kevin (fetch + diagnóstico con curl)
- Diagnóstico del bloqueo de Japón: 403 con y sin headers de navegador, también MOFA y home de la embajada → conclusión: bloqueo por huella TLS (WAF), definida estrategia de 4 niveles (PLAN §4)
- Verificado: Australia ofrece los datos del subclass 462 en HTML estático (200 vía curl) — el 403 anterior era del servicio webfetch
- Acuerdo de ajuste Canadá: usar `eligibility-by-country.html` (HTML estático) en vez de la variante con `?selection=cl-wh` (JS)
- Creados los 3 documentos de gobierno del proyecto: PLAN.md, ROADMAP.md, BITACORA.md

**Hallazgos relevantes:**
- Irlanda: 200 cupos/año, 2 rondas de 100, aplica por **un solo email** entre 9–10 a.m. → concepto temporal delicado: el aviso oportuno del bot es crítico
- Nuevo Zelanda: la página muestra un badge "Closed" explícito (hoy cerrada para 2026; 940 visas/año) — keyword trivial
- Australia: HTML con "Chile", "462" y texto de cupos confirmado en crudo
- Japón: única fuente difícil; el acceso podría funcionar desde GitHub Actions (IP/entorno distinto) — primera prueba a hacer al llegar a Etapa 6
- Acción pendiente del usuario en Etapa 2: guardar HTML de AU, IE y JP desde el navegador como fixtures

**Pendientes para la próxima sesión:**
- Etapa 1 completa (agente de build): git init, estructura, pyproject, .gitignore, README, main.py mínimo

**Estado al cierre:** Planificación completa ✅ — proyecto listo para entrar a Etapa 1

------------------------------------------------------------

## 2026-11-10 | ETAPA 1 — Preparación del proyecto
**Agente:** opencode GLM-5.3-Flash-Free (build, sesión con Kevin)

**Qué se hizo:**
- Repositorio git inicializado; documentos de gobierno (PLAN/ROADMAP/BITACORA) copiados a `docs/` — desde ahora la versión viva vive en el repo
- Estructura completa creada: `src/` (con `main.py` esqueleto y paquete `collectors`), `config/`, `data/`, `tests/fixtures/`
- `pyproject.toml` configurado (Python >=3.11 por compatibilidad con el local de Kevin; Actions correrá 3.12): deps `httpx` + `beautifulsoup4`, dev-deps `pytest`/`pytest-mock`/`ruff`, config de pytest y de ruff (línea 100)
- `.gitignore` con nota explícita de que `data/state.json` SÍ se commitea (D3) y exclusión de `.agents/` (recursos internos del entorno, generaban 17 errores de ruff)
- README con introducción, guía para agentes de IA, estructura y uso local
- `.venv` creada y dependencias instaladas; test smoke `tests/test_smoke.py` (semilla del estilo TDD)

**Hallazgos relevantes:**
- Python local de Kevin es 3.11.9 (no 3.12) → `requires-python = ">=3.11"` y `target-version = "py311"`
- La carpeta `.agents/` del entorno no debe entrar al repo ni al linter — excluida en `.gitignore` y `extend-exclude` de ruff

**Pendientes para la próxima sesión:**
- Etapa 2 paso 0: Kevin guarda HTML desde el navegador como `tests/fixtures/{au,ie,jp}.html`
- Etapa 2: TDD de `collectors/base.py` con mocks HTTP (.fetch ok / timeout / 403 / HTML vacío)

**Estado al cierre:** Etapa 1 completada ✅ — `python -m src.main` OK · `pytest` 1 passed · `ruff` limpio · commit inicial incluido en esta misma sesión

------------------------------------------------------------

## 2026-11-10 | ETAPA 2 — Sistema de extracción (TDD)
**Agente:** opencode GLM-5.3-Flash-Free (build, sesión continua)

**Qué se hizo:**
- Commiteo de los 5 fixtures HTML entregados por Kevin (assets `*_files` excluidos del repo — solo `.html` sirve para scraping)
- Resolución del caso Canadá por verificación live (página `become-candidate` con banner de temporada)
- TDD del colector base: `fetch_page()` + `SourceError` (6 tests: 200, 403, vacío, timeout×2, red, headers)
- TDD del scraper con 3 métodos de extracción (6 tests): `extract_text` genérico, `extract_row_text` (fila ancla, contra el fixture REAL de Australia), `extract_selector_text` (CSS, contra el fixture REAL de NZ)
- TDD de `config.py` (8 tests): `CountryConfig` dataclass, validación de 5 bloques TOML, errores claros por país/falta de campo, `tests/fixtures/` comiteados
- `countries.toml` finalizado con url+keywords por país, ES la configuración de truths para tests

**Hallazgos relevantes:**
- 🇦🇺 Australia: `<tr>` de Chile `<span class="label label-success">Open</span>` y **3,400 cupos**; método "fila" con ancla "Chile" (extraído directo, en la página hay más países con "Open")
- 🇳🇿 NZ: correcto selector es `.visa-page__status-wrapper` (modificador `--closed` / `--open`); hoy cerrado para 2026
- 🇯🇵 **HALLAZGO IMPORTANTE:** el fixture REAL muestra "Apertura del agendamiento de citas — Desde el 2 de noviembre de 2026, 9:00 a.m." → nota oportuna para avisar a Kevin (podría ser una abertura VIGENTE)
- 🇨🇦 **Canadá RESUELTO:** la página correcta es `become-candidate.html` con banner "IEC season is closed"/"open" — coincide AL 100% con la estrategia de keywords. La página `eligibility-by-country` solo lista requisitos sin estado de rondas
- 🧪 Nota para etapa 3: IE y JP usan `metodo="texto"` con keyword provisional — el orquestador tendrá tolerancia a `None` en extraer (predicciones sobre "fila" van a fadeIn de ignorancia en algunos países). JP: bloqueo TLS sigue activo para curl/webfetch — fixture del navegador mantiene truth para el desarrollo
- Fixture `cad.html` = página del selector JS (no sirve como estático) queda en repo como referencia histórica

**Pendientes para la próxima sesión:**
- Etapa 3: TDD de `detection.py` (motor de detección con las reglas R1-R4)
- Etapa 3: TDD de `state.py` (persistencia de snapshots en `data/state.json`)

**Estado al cierre:** Etapa 2 completada ✅ — 22 tests verde, ruff limpio

------------------------------------------------------------

## 2026-11-10 | ETAPA 3 — Motor de deteccion + Persistencia (TDD) + colector navegador
**Agente:** opencode GLM-5.3-Flash-Free (build, sesion continua)

**Que se hizo:**
- TDD de `detection.py`: `clasificar()` (keywords sobre texto normalizado), `decidir()` (siembra/sin_cambios/apertura/cierre/cambio), `decidir_fallo()` (R3: ignore 1er fallo, alerta en el 2do)
- TDD de `state.py`: `Snapshot` frozen + JSON round-trip + tolerancia a archivo corrupto/inexistente
- TDD de `correr()` en `main.py`: funcion PURA del flujo de una corrida (alertas + contador de fallas + independencia entre paises)
- `main.py` real end-to-end: `recolectar()` (despacha por `pais.acceso`) -> `correr()` -> `guardar()`, siempre exit 0
- Descarga del scraper: normalizacion de caracteres fantasma (`\u200b`/nbsp) + decodificador charset (bs4 gasleck jetidge sin meta charset)
- **Correctiva TDD importante:** snapshot placeholder de una siembra fallida (texto="") + recuperacion = SIEMBRA, no CIERRE falso (R1)

**Hallazgos relevantes (Nivel 4 del plan activado con evidencia):**
- 🇳🇿 NZ (Incapsula) no pasa ni con Chromium headless "plain": implementado `collectors/browser.py` Chromium **headful** + `--disable-blink-features=AutomationControlled` + reload hasta 3 veces: **UN PASAJE con cookies resuelve el challenge** (pase 0: 686KB, "closed for" presente). Config nuevo: campo `acceso = "http" | "navegador"`
- 🇨🇦 CA: en local httpx/requests/curl TODOS timeout a canada.ca (ruta Akamai/chile) — pero con Chromium headful pasa y trae el banner "IEC season is closed" (190KB). Tuvo tunel 404 por typo `Services` vs `services` — corregido
- 🇯🇵 JP: .go.jp TLS WAF SSE — con Chromium headful **SI PASA** (46KB + "apertura del agendamiento" localizado); campo `acceso = "navegador"` en config
- **CORRIDA REAL FINAL 5/5 OK:** AU "Open 3,400" (abierto) / CA "season is closed" / NZ "closed for 2026" / JP "apertura del agendamiento" (abierto: notificara cuando la tarjeta apague en etapa 4) / IE desconocido
- 2nd corrida idempotente: 0 alertas duplicadas

**Pendientes para la próxima sesión:**
- Etapa 4: TDD de `notify.py` (embeds Discord por tipo de decision) + webhook de pruebas de Kevin
- Etapa 3.x refinamiento (opcional): los snapshots de CA/IE guardan texto COMPLETO oase (10-40KB con menus) — considerar ventana/recorte alrededor de seccion relevante para reduccion de falsos CAMBIO

**Estado al cierre:** Etapa 3 completada ✅ — 55 tests verde; ruff limpio; `python -m src.main` corre las 5 fuentes reales sin errores


