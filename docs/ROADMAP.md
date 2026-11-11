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
- [x] Prueba de envío real: **Kevin crea los webhooks él mismo** — por seguridad NUNCA se comparten por chat con agentes (D9). La verificación del flujo completo se hace con `tools/simular_discord.py` (webhook simulado local, sin credenciales); la entrega real a Discord se valida con la 1ª corrida en Actions (secretos ya configurados por Kevin)

✅ **Cierre:** capturas de los mensajes en Discord definidas (descripción textual en la bitácora) + suite de notify verde.

---

## Etapa 4b — Mensajería para comunidad grande (decisions D9/D10, PLAN §8)

**Contexto:** el bot sirve a la comunidad de Discord de un youtuber. Reglas del producto en PLAN §8: evidencia verificable, noticia ≠ convocatoria, cambios menores fuera del canal público, fuente inaccesible solo a staff, hora de detección explícita, cero menciones, cero saturación.

- [x] **TDD `notify.py`:** campo **"Detectado"** (hora Chile) + campo **"Evidencia"** (cita literal de la fuente) en apertura/cierre; `allowed_mentions: {"parse": []}` en todo payload; footer "detección automática"; redacción profesional
- [x] **TDD `detection.py`:** `evidencia()` (cita ~120 chars alrededor de la keyword matcheada); `clasificar()` respeta `contexto` por país (co-ocurrencia en ventana ~250 chars → una noticia de otro programa ya no dispara apertura)
- [x] **TDD `correr()` en `main.py`:** cooldown **24 h** por país+tipo (`alertas_enviadas` en Snapshot/state.json, tolerante a estados viejos) + tope **3 embeds/corrida** con prioridad apertura > cierre > fuente_inaccesible > cambio (`seleccionar_alertas()`)
- [x] **Ruteo 2 canales en `main.notificar()`:** apertura/cierre → `DISCORD_WEBHOOK_URL` (público); cambio/fuente_inaccesible → `DISCORD_WEBHOOK_ADMIN_URL` (admin); falta admin → solo log; pausa 1 s entre envíos; `[alertas]` en countries.toml con `cooldown_horas`/`max_embeds_corrida`
- [x] **Anti-ruido estructural:** `selector_seccion = "main"` para CA e IE (snapshot solo sección de contenido, sin menús) — reduce falsos CAMBIO hacia el canal admin
- [x] **Prueba SIN credenciales (seguridad, D9):** `tools/simular_discord.py` — servidor HTTP local que hace de webhook. Verificado en vivo: ruteo público/admin correcto (JP apertura → público; CA cambio → admin), evidencia literal de la embajada en el embed público, "Detectado" con hora de Chile, `allowed_mentions: {"parse": []}`, footer automático, estado del repo restaurado sin contaminar. La entrega real a Discord se valida con la 1ª corrida en Actions

✅ **Cierre:** suite verde (91 tests) + ruff limpio; corrida real 5/5 post-siembra sin falsos CAMBIO; embeds sin menciones y con evidencia **verificados por simulación local sin exponer credenciales**; la entrega real de Discord se confirma en la 1ª corrida de la Etapa 6.

---

## Etapa 5 — Persistencia revisada + inicialización

**Responsable agente:** retro-compatibilidad con datos ya existentes (el `state.json` se va a commitear, va a vivir en historial).

- [ ] Semilla inicial empaquetada: si `data/state.json` no existe → modo siembra silenciosa explícito, logs claros en la corrida
- [ ] **TDD:** cargar un `state.json` de formato antiguo no rompe nada (tolerancia a evolución del formato)
- [x] `.gitattributes` con EOL normalizado (`data/state.json`, TOML, Python, YAML a LF) — hecho en Etapa 4b
- [ ] Verificar exit codes: la corrida que detecta algo notifica y termina 0; el fallo NO debe dejar Actions rojo (el monitoreo silently falla, no rompe el build)

✅ **Cierre:** simulación local de 3 corridas seguidas → solo notifica lo que cambia; nada se repite.

---

## Etapa 6 — GitHub Actions

**Acciones de Kevin:** crear los **2 secretos** en el repo GitHub: `DISCORD_WEBHOOK_URL` (canal público de comunidad) y `DISCORD_WEBHOOK_ADMIN_URL` (canal de staff). Opcional: disparar una corrida manual con el botón "Run workflow" (workflow_dispatch) en la pestaña Actions.

- [x] `.github/workflows/check.yml`: cron `0 */4 * * *` (UTC) + `workflow_dispatch` + `timeout-minutes: 40` + `concurrency` (corridas encoladas, nunca se pisan)
- [x] Permisos mínimos (`contents: write`) + auto-commit de `data/state.json` (`stefanzweifel/git-auto-commit-action@v5`, solo si la corrida fue exitosa)
- [x] Configurar Python 3.12 en el workflow (setup-python + cache de pip) + Chromium de Playwright (`--with-deps`) + **xvfb** para el Chromium headful (runners sin display)
- [ ] **Prueba Nivel 2 PLAN §4:** primera corrida real de los 5 países desde Actions (schedule automático o botón manual) — confirma si AU/CA/NZ/JP responden desde IPs de datacenter. Registrar el resultado en BITACORA.md
- [ ] Si algún país queda bloqueado desde Actions: ajustar URLs de respaldo (Nivel 3) o afinar el colector navegador (Nivel 4, ya implementado)

✅ **Cierre:** 2 corridas automáticas exitosas en Actions; se confirma por el último commit de `data/state.json` en GitHub.

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
| 4b — Mensajería comunidad | ✅ **Completada** (verificada con simulador local sin credenciales) | 2026-11-11 |
| 5 — Persistencia revisada | 🟡 En marcha (.gitattributes hecho; falta TDD de tolerancia + semilla explícita) | 2026-11-11 |
| 6 — GitHub Actions | 🟡 Workflow listo (falta 1ª corrida real en Actions + 2 secretos) | 2026-11-11 |
| 7 — Pruebas y lanzamiento | ⬜ Pendiente | — |
