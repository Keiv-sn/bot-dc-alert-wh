# PLAN — Bot de Alertas Working Holiday Chile 🇨🇱

> Documento maestro del proyecto. Cualquier agente debe leer este archivo, ROADMAP.md y BITACORA.md antes de escribir código.

## 1. Propósito

Bot en Python que monitorea las páginas oficiales de los programas Working Holiday (WHA/W&H) accesibles para ciudadanos chilenos en **cinco países**, detecta cuando una convocatoria **abre, cierra o cambia**, y notifica inmediatamente por **Discord (webhook)**. Corre 24/7 en **GitHub Actions** sin necesidad de PC encendida.

## 2. Decisiones ya acordadas (NO re-discutir, son cerradas)

| # | Decisión | Detalle |
|---|----------|---------|
| D1 | Países | Australia, Canadá, Irlanda, Nueva Zelanda, Japón |
| D2 | Método de detección | **Palabras clave configuradas por país** en `config/countries.toml` (no hash de página completa) |
| D3 | Persistencia | `data/state.json` **commiteado al repo** (GitHub Actions hace auto-commit) |
| D4 | Frecuencia | Cron **cada 4 horas** (`0 */4 * * *`) |
| D5 | Discord | Webhook HTTP puro (POST) — sin librería de bot, sin procesos persistentes |
| D6 | Stack | Python 3.12 · httpx + beautifulsoup4 · pytest · ruff |
| D7 | Metodología | **TDD** (red → green → refactor) en etapas 2–5 |
| D8 | Calidad | Principios de código limpio (ver §6) obligatorios |

## 3. Fuentes oficiales (estado al 2026-11-09)

| País | URL | Estado de verificación |
|------|-----|------------------------|
| Australia | `https://immi.homeaffairs.gov.au/what-we-do/whm-program/status-of-country-caps` | ✅ **200 vía curl**, datos de Chile + subclass 462 en HTML estático. Pendiente: confirmar que IPs de GitHub Actions no estén bloqueadas (Etapa 6). El 403 reportado antes era del servicio webfetch, no del sitio |
| Canadá | `https://www.canada.ca/en/immigration-refugees-citizenship/services/work-canada/iec/eligibility/eligibility-by-country.html` | ✅ Página del IEC accesible. **AJUSTE ACORDADO:** no usar la URL con `?selection=cl-wh` (el detalle se expande con JavaScript); usar `eligibility-by-country.html` que es HTML estático |
| Irlanda | `https://www.ireland.ie/en/chile/santiago/services/visas/chile-working-holiday-agreement/` | ✅ Excelente. Datos verificados: 200 cupos/año en **2 rondas de 100**, postulación por email a `irishwhchile@vfsglobal.com` en franja 9–10 a.m. de fechas anunciadas. Fuente secundaria: sección "news and events" de la embajada |
| Nueva Zelanda | `https://www.immigration.govt.nz/visas/chile-working-holiday-visa/` | ✅ Excelente. Badge de estado explícito; hoy muestra **"Closed"** para 2026 (940 visas/año). Detección trivial por keywords |
| Japón | `https://www.cl.emb-japan.go.jp/itpr_es/WorkingHolidayChileJapon.html` | ⚠️ **403 con y sin headers de navegador** (también MOFA Tokio y el home de la embajada). Diagnóstico: bloqueo por huella TLS (WAF), no por User-Agent. Estrategia completa en §4 |

## 4. Estrategia acordada para Japón (y bloqueos en general) — 4 niveles

1. **Nivel 1 — Desbloquear desarrollo ya:** usuario guarda el HTML inicial de Australia/Japón desde su navegador (Ctrl+S) → se usan como **fixtures de test** y referencia de keywords. El desarrollo del resto del sistema NO espera a resolver el acceso.
2. **Nivel 2 — Probar desde GitHub Actions:** el entorno/IP de Actions es distinto; puede que .go.jp responda 200 a Python desde ahí. Se prueba primero (gratis).
3. **Nivel 3 — URLs de respaldo:** cada país en `countries.toml` declara `url_primaria` + reservas de respaldo (Irlanda: news/events; Japón: CLAIR u otras páginas de la embajada / notas de Cancillería de Chile).
4. **Nivel 4 — Última instancia:** colector avanzado `JapanPlaywrightCollector` con Chromium headless (Playwright) instalado en el workflow. **Debe respetar la misma interfaz del colector base** — un país más complejo no debe tocar el resto del sistema.

## 5. Arquitectura

```
bot-dc-wh/
├── src/
│   ├── main.py            # orquestador: colectar → detectar → notificar → guardar
│   ├── config.py          # carga y valida countries.toml → dataclasses tipadas
│   ├── collectors/
│   │   ├── base.py        # fetch con headers de navegador, timeout, retry, manejo de errores
│   │   ├── scraper.py     # colector HTML genérico (cubre 4 de 5 países)
│   │   └── playwight_jp.py  # (solo si Nivel 4 necesario) — MISMA interfaz que base
│   ├── detection.py       # normalización + keywords + comparación con snapshot previo
│   ├── notify.py          # formato de embeds → POST al webhook de Discord
│   └── state.py           # cargar/guardar data/state.json (tolerante a archivo corrupto)
├── config/countries.toml  # UN bloque por país: url, url_respaldo, keywords, método
├── data/state.json        # estado persistido (commiteado)
├── tests/
│   ├── fixtures/          # HTML real guardado por país (fuente de truth)
│   └── ...                # pytest
├── .github/workflows/check.yml   # cron 4h + secretos + auto-commit del estado
└── README.md · .gitignore · pyproject.toml
```

**Flujo de una corrida:** colectar HTML de los 5 países (independiente entre sí) → detectar decisión por país → notificar webhook por cada cambio real → guardar nuevo estado.

## 6. Principios de código limpio (compromiso, aplica a todo PR)

1. **Nombres legibles:** `detect_changes()` no `proc()`; `AustraliaCollector` no `C1`.
2. **Responsabilidad única:** ninguna función de más de ~20 líneas; cada módulo una sola capa del flujo.
3. **Type hints** en toda la firma de funciones y modelos.
4. **Config como datos, no código:** todo lo volátil (URLs, keywords, umbrales) vive en `countries.toml`; el código solo define *cómo* interpretar la config. Agregar un país #6 = agregar un bloque TOML, cero código nuevo.
5. **Sin estado global mutable:** el estado se pasa explícitamente entre funciones.
6. **Funciones puras donde se pueda:** la detección debe ser `f(snapshot_previo, html_nuevo) → decisión` determinista y 100% testeable.
7. **Errores explícitos:** no `try/except` silenciosos; los fallos de coleccionas se propagan clasificados (timeout/403/parseo).
8. **Formateo automático:** `ruff` como linter/formatter; todo el código pasa el linter antes de merge.

## 7. Reglas de negocio del detector (evitar alarmas falsas y chat spam)

| Regla | Comportamiento |
|-------|----------------|
| R1 — Primera corrida | "Siembra silenciosa": guarda estado inicial de los 5 países **sin notificar** |
| R2 — Cambio real | Solo notifica si el estado **clasificado** cambia (ABIERTA→CERRADA→ABIERTA o texto de cupos/keywords clave cambia semánticamente) |
| R3 — Error ≠ cambio | Página caída/403/timeout NO es cambio. Solo avisa al usuario tras **2 fallos consecutivos** del mismo país (alerta de "fuente inaccesible") |
| R3 — Sin duplicados | Si el estado no cambió respecto al snapshot, **no** se notifica (idempotente) |
| R4 — Un país falla ≠ todo falla | Fallos de una fuente no impiden procesar las otras 4 |

## 8. Mensajes de Discord (diseño acordado)

- Embeds con color por tipo: 🟢 **Apertura de convocatoria**, 🔄 Cambio relevante (requisitos/cupos), 🔴 Fuente inaccesible persistente, ℹ️ Info (siembra inicial silenciosa — solo log, no mensaje).
- Cada mensaje incluye: país (flag + nombre), qué pasó, enlace directo a la fuente, fecha/hora en hora chilena (CLT), cupos si la página los informa.
- Coordenadas del webhook en secreto de GitHub Actions (`DISCORD_WEBHOOK_URL`), nunca en el repo.

## 9. Fuera de alcance (explícito)

- No automatizar postulación ni llenado de formularios.
- No usar cuentas de correo del usuario ni credenciales de portales de visa.
- No vigilar Instagram de la embajada irlandesa por ahora (fuente secundaria manual).
- No base de datos: JSON es suficiente para el volumen.

## 10. Departamentos de trabajo (responsabilidades típicas al partir cada etapa)

- **Usuario Kevin:** decidir dudas de producto, guardar HTML/fixtures del navegador cuando se pidan, crear el webhook de Discord y el repo remoto en GitHub, configurar el secreto.
- **Agente (cualquiera):** seguir ROADMAP etapa por etapa, respetar D1–D8 y §6/§7, escribir tests primero, **registrar cada hito/hallazgo en BITACORA.md al cierre de su sesión**, nunca saltarse la bitácora.
