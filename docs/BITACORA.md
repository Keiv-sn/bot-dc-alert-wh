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
