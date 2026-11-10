# ROADMAP — Bot de Alertas Working Holiday Chile 🇨🇱

> Hoja de ruta etapa por etapa, en el orden acordado. Cada agente toma **una etapa completa (hasta el criterio de cierre)** antes de pasar a la siguiente, y actualiza BITACORA.md al terminar.

## Convenciones

- ✅ = criterio de cierre verificable de la etapa.
- **TDD:** todos los módulos de las etapas 2–5 se escriben test-first (ver PLAN §7 D7).
- Al finalizar cada etapa: registrar en BITACORA.md, hacer commit con mensaje claro, y marcar la etapa con fecha de cierre en la tabla resumen del final de este archivo.
- Las etapas usan el "modo build" de OpenCode; este documento se consulta, no se re-escribe.

---

## Etapa 1 — Preparación del proyecto

**Responsable agente:** estructura + configuración. **Responsable usuario:** crear repo remoto en GitHub (se pedirá al final).

- [ ] `git init` en `C:\Users\Kevin\Desktop\bot-dc-wh` + primer commit
- [ ] Estructura de carpetas según PLAN §5 (con `__init__.py` donde corresponde)
- [ ] `pyproject.toml`: python 3.12, deps (`httpx`, `beautifulsoup4`), dev-deps (`pytest`, `pytest-mock`, `ruff`)
- [ ] `.gitignore` de Python + regla adicional: ignorar nada del contenido de `data/` (el estado SÍ se commitea)
- [ ] `README.md` con: qué hace el bot, cómo configurarlo, cómo correrlo local, cómo interpretar las alertas
- [ ] Un `main.py` mínimo en pie (corre y termina con exit 0, imprime "ok") para verificar setup

✅ **Cierre:** `pytest` y `ruff` corren sin errores en repo limpio; `python -m src.main` ejecuta y termina OK.

---

## Etapa 2 — Sistema de extracción (5 países)

**Paso 0 (acción de Kevin):** guardar desde el navegador como HTML, en `tests/fixtures/`: `au.html`, `ie.html`, `jp.html` (+ `cl.html` si aparecen nuevas fuentes). Se pide con nombre de archivo exacto al llegar aquí.

- [ ] **TDD `collectors/base.py`** con mocks HTTP: 200 válido, timeout, 403, HTML vacío, red caída → errores clasificados (`SourceError(tipo)`)
- [ ] Headers de navegador real en el fetch (ver PLAN §4 Nivel 2/3 pb Japón)
- [ ] **TDD `collectors/scraper.py`**: dado fixture HTML → texto normalizado de la sección relevante (dado el país y su método de extracción en la config)
- [ ] `config/countries.toml` con los 5 bloques: `url`, `url_respaldo` (si aplica), `keywords_abierto`, `keywords_cerrado`, `metodo_extraccion`
- [ ] **TDD `config.py`:** carga TOML → dataclasses validadas; error claro si falta un campo o país
- [ ] Chequeo manual real contra `immi.homeaffairs.gov.au` y `canada.ca` (las 2 fuentes con más incertidumbre de estructura)

✅ **Cierre:** cada collector devuelve texto normalizado desde su fixture real; suite de tests de collectors verde.

---

## Etapa 3 — Motor de detección + Persistencia (acordadas como EL MOMENTO importante — etapas 3 y 5 del plan original fusionadas, ver PLAN §7)

- [ ] **TDD `detection.py`:** `f(snapshot_previo, html_nuevo) → Decision(tipo, detalles?)`. Casos obligatorios:
  - [ ] Primera corrida → `SIEMBRA` (no notifica) [R1]
  - [ ] abierto→abierto → `SIN_RECAMBIO` [R2]
  - [ ] cerrado→abierto → `APERTURA` ✅ notifica
  - [ ] abierto→cerrado → `CIERRE` (notifica; útil si se reabre después)
  - [ ] keywords cambian sin abrir/cerrar → `CAMBIO` con detalle de las diferencias
  - [ ] 2 fallos consecutivos misma fuente → `FUENTE_INACCESIBLE` (1 fallo → `IGNORE` silencioso) [R3]
  - [ ] país 1 falla ≠ afecta decisión de países 2–5 [R4]
- [ ] **TDD `state.py`:** round-trip JSON, tolerante a JSON corrupto (regenera desde cero como siembra), snapshot por país con timestamp
- [ ] `main.py` orquesta **solo lenguaje declarativo**: colectar (aunque un país falle) → detectar → notificar → guardar

✅ **Cierre:** toda la lógica de negocio está en funciones puras testeables; suite de detección verde cubriendo R1–R4.

---

## Etapa 4 — Notificaciones Discord

**Acción de Kevin:** crear webhook en un servidor de Discord de pruebas y darlo al agente como valor, o guardarlo en secret/env var local para pruebas manuales (nunca commitear el webhook real).

- [ ] **TDD `notify.py`:** payload correcto por tipo de decisión: embeds, color, título (🟢/🔄/🔴), URL de fuente, hora CLT
- [ ] POST asincrono con timeout y un solo `retry` (fallas de Discord no tumbean la corrida)
- [ ] Prueba manual con webhook de pruebas → 3 mensajes reales (apertura simulada, cambio simulado, error simulado)

✅ **Cierre:** capturas de los mensajes en Discord definidas (descripción textual en la bitácora) + suite de notify verde.

---

## Etapa 5 — Persistencia revisada + inicialización

**Responsable agente:** retro-compatibilidad con datos ya existentes (el `state.json` se va a commitear, va a vivir en historial).

- [ ] Semilla inicial empaquetada: si `data/state.json` no existe → modo siembra silenciosa explícito, logs claros en la corrida
- [ ] **TDD:** cargar un `state.json` de formato antiguo no rompe nada (tolerancia a evolución del formato)
- [ ] `.gitattributes` si se detecta ruido de diffs (ej. carga asimétrica con longa estampa de tiempo — decidir formato JSON compacto)
- [ ] Verificar exit codes: la corrida que detecta algo notifica y termina 0; el fallo NO debe dejar Actions rojo (el monitoreo silently falla, no rompe el build)

✅ **Cierre:** simulación local de 3 corridas seguidas → solo notifica lo que cambia; nada se repite.

---

## Etapa 6 — GitHub Actions

**Acciones de Kevin:** subir repo remoto + crear el secreto `DISCORD_WEBHOOK_URL`.

- [ ] `.github/workflows/check.yml`: cron `0 */4 * * *` (UTC → revisar hora chilena) + `workflow_dispatch` (para pruebas manuales) + timeout de la corrida
- [ ] Permisos mínimos + acción de auto-commit del `data/state.json` (acción recomendada: `stefanzweifel/git-auto-commit-action`)
- [ ] Configurar Python 3.12 en el workflow (setup-python + cache de pip)
- [ ] **Prueba Nivel 2 PLAN §4:** correr callback real de los 5 países desde Actions — aquí se confirma si Australia y Japón responden 200 desde datacenter. Registrar el resultado en BITACORA.md
- [ ] Si Japón (o Australia) queda bloqueado desde Actions: aumentar Nivel 3 (URLs respaldo) en `countries.toml` o pasar a Nivel 4 (`playwright` en el workflow)

✅ **Cierre:** 2 corridas automáticas exitosas en Actions; se confirma por último commit de `data/state.json` en GitHub.

---

## Etapa 7 — Pruebas y lanzamiento

**Responsable agente:** testing de confiabilidad. **Responsable Kevin:** decidir momento de "ir de verdad".

- [ ] Simular apertura insertando fixture HTML modificado en `tests/` y verificando E2E (corrida completa local)
- [ ] Simular cambio de requisitos (fixture con texto distinto pero sin abrir)
- [ ] Simular caída página (timeout/403 repetido) → confirmar regla R3 (solo avisa a la 2ª vez)
- [ ] Simular notificaciones duplicadas (mismo snapshot corrido 2 veces) → confirmar cero mensajes repetidos
- [ ] Checklist de lanzamiento: secreto productivo, cron activo, `data/state.json` con estado de "siembra real", README actualizado
- [ ] **Activar monitoreo definitivo** 🚀 (Kevin da el visto bueno)

✅ **Cierre:** monitoreo real activo. Proyecto en modo mantenimiento.

---

## Registro de etapas cerradas (fecha en BITACORA.md)

| Etapa | Estado | Fecha cierre |
|-------|--------|--------------|
| 1 — Preparación | ✅ **Completada** | 2026-11-10 |
| 2 — Extracción | ⬜ Pendiente | — |
| 3 — Detección + Estado | ⬜ Pendiente | — |
| 4 — Discord | ⬜ Pendiente | — |
| 5 — Persistencia revisada | ⬜ Pendiente | — |
| 6 — GitHub Actions | ⬜ Pendiente | — |
| 7 — Pruebas y lanzamiento | ⬜ Pendiente | — |
