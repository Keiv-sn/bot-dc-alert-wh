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

- [x] **TDD `collectors/base.py`** con mocks HTTP: 200 válido, timeout, 403, HTML vacío, red caída → errores clasificados (`SourceError(tipo)`); headers de navegador real; reintento solo para red/timeout
- [x] **TDD `collectors/scraper.py`**: `extract_text` (texto completo), `extract_row_text` (Australia), `extract_selector_text` (NZ) — probados contra fixtures REALES
- [x] `config/countries.toml` con los 5 bloques: `url`, `url_respaldo` (opcional), `keywords_abierto`, `keywords_cerrado`, `metodo` (texto/fila/selector)
- [x] **TDD `config.py`:** carga TOML → dataclasses `CountryConfig` validadas; errores claros por campo faltante o método inválido
- [x] Verificación live de fuentes inciertas: **Canadá** resuelta (`become-candidate.html` con banner "IEC season is open/closed"); AU responde 200 desde conexión local

✅ **Cierre:** cada collector devuelve texto normalizado desde su fixture real; suite de tests de collectors verde.

---

## Etapa 3 — Motor de detección + Persistencia (acordadas como EL MOMENTO importante — etapas 3 y 5 del plan original fusionadas, ver PLAN §7)

- [x] **TDD `detection.py`:** `clasificar()`, `decidir()`, `decidir_fallo()` — todas las reglas R1-R4 cubiertas (incl. snapshot placeholder de una siembra fallida → siembra, evitando cierre falso)
- [x] **TDD `state.py`:** `Snapshot` + round-trip JSON, tolerante a JSON corrupto (regenera desde cero como siembra)
- [x] **TDD `correr()`** en `main.py`: flujo de corrida puro y testeable (8 tests): alertas, fallos consecutivos, países independientes
- [x] **`main.py` orquesta real end-to-end:** recolectar (http o navegador según config) → detectar → alertar → guardar, SIEMPRE exit 0
- [x] **Colector navegador (Nivel 4 activado por evidencia):** `collectors/browser.py` con Chromium headful + reload de challenge — resuelve CA (Akamai), NZ (Incapsula), JP (TLS WAF); campos `acceso` en config y tests
- [x] Normalización de caracteres fantasma (\u200b/nbsp) y decodificador de charset explícito (scroll findings)

✅ **Cierre:** toda la lógica de negocio está en funciones puras testeables; suite de detección verde cubriendo R1–R4. **[2026-11-10 CORRIDA REAL 5/5 VERIFICADA: AU abierto; CA cerrado; NZ cerrado; JP abierto (agendamiento vigente); IE desconocido (indirecto)]**

---

## Etapa 4 — Notificaciones Discord

**Acción de Kevin:** crear webhook en un servidor de Discord de pruebas y darlo al agente como valor, o guardarlo en secret/env var local para pruebas manuales (nunca commitear el webhook real).

- [x] **TDD `notify.py`:** payload correcto por tipo de decision: embeds, color, título (🟢/🔴/🔄/⚠️), URL de fuente, horario CLT (`America/Santiago` con tzdata); envío POST con un solo reintento (httpx.MockTransport) tolerante a fallos
- [x] Integración: `main.notificar()` — webhook por var de entorno `DISCORD_WEBHOOK_URL`; sin webhook → solo log, exit 0 igual
- [ ] Prueba manual con webhook de pruebas → 3 mensajes reales (apertura simulada, cambio simulado, error simulado) **[pendiente: Kevin debe entregar la URL del webhook]**

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
| 2 — Extracción | ✅ **Completada** | 2026-11-10 |
| 3 — Detección + Estado | ✅ **Completada** (corrida real 5/5 verificada) | 2026-11-10 |
| 4 — Discord | 🟡 En marcha (falta prueba manual con webhook) | 2026-11-10 |
| 5 — Persistencia revisada | ⬜ Pendiente | — |
| 6 — GitHub Actions | ⬜ Pendiente | — |
| 7 — Pruebas y lanzamiento | ⬜ Pendiente | — |
