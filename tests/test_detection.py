"""Tests del motor de deteccion (docs/PLAN.md R1-R4 + D10). Funciones puras."""

from src.config import CountryConfig
from src.detection import clasificar, decidir, decidir_fallo, evidencia
from src.state import Snapshot


def pais(
    codigo: str = "au",
    abierto: list[str] | None = None,
    cerrado: list[str] | None = None,
    contexto: str = "",
) -> CountryConfig:
    return CountryConfig(
        codigo=codigo,
        nombre=codigo,
        url="https://ejemplo",
        metodo="texto",
        keywords_abierto=abierto or [],
        keywords_cerrado=cerrado or [],
        contexto=contexto,
    )


class TestClasificar:
    def test_keyword_abierta_clasifica_abierto(self) -> None:
        assert clasificar("<p>season is open</p>", pais(abierto=["season is open"])) == "abierto"

    def test_keyword_cerrada_clasifica_cerrado(self) -> None:
        assert clasificar("closed for 2026", pais(cerrado=["closed for"])) == "cerrado"

    def test_sin_ninguna_keyword_es_desconocido(self) -> None:
        assert clasificar("documentos varios", pais(abierto=["open"])) == "desconocido"

    def test_conflicto_abre_y_cierra_es_desconocido(self) -> None:
        texto = "open y closed"
        assert clasificar(texto, pais(abierto=["open"], cerrado=["closed"])) == "desconocido"

    def test_keywords_case_insensitive(self) -> None:
        assert clasificar("A N C H O R Open", pais(abierto=["open"])) == "abierto"


class TestDecidir:
    SNAPSHOT_ABIERTO = Snapshot(estado="abierto", texto="open")
    SNAPSHOT_CERRADO = Snapshot(estado="cerrado", texto="closed")

    def test_sin_snapshot_es_siembra(self) -> None:
        decision = decidir(pais(abierto=["open"]), None, "open")
        assert decision.tipo == "siembra"
        assert decision.estado == "abierto"

    def test_texto_igual_es_sin_cambios(self) -> None:
        decision = decidir(pais(abierto=["open"]), self.SNAPSHOT_ABIERTO, "open")
        assert decision.tipo == "sin_cambios"
        assert decision.estado == "abierto"

    def test_cerrado_a_abierto_es_apertura(self) -> None:
        decision = decidir(
            pais(abierto=["open"], cerrado=["closed"]), self.SNAPSHOT_CERRADO, "open",
        )
        assert decision.tipo == "apertura"
        assert decision.estado == "abierto"

    def test_abierto_a_cerrado_es_cierre(self) -> None:
        decision = decidir(
            pais(abierto=["open"], cerrado=["closed"]), self.SNAPSHOT_ABIERTO, "closed",
        )
        assert decision.tipo == "cierre"
        assert decision.estado == "cerrado"

    def test_texto_cambia_manteniendo_estado_es_cambio(self) -> None:
        previo = Snapshot(estado="abierto", texto="open clases 100")
        decision = decidir(pais(abierto=["open"]), previo, "open clases 200")
        assert decision.tipo == "cambio"
        assert decision.estado == "abierto"

    def test_desconocido_con_nuevo_texto_es_cambio(self) -> None:
        previo = Snapshot(estado="desconocido", texto="a")
        decision = decidir(pais(), previo, "b")
        assert decision.tipo == "cambio"

    def test_snapshot_placeholder_fallido_primedera_recuperacion_es_siembra(self) -> None:
        # pais que fallo en la siembra (placeholder texto="") + recupera ->
        # NO debe alertar cierre/apertura falso (docs/PLAN.md R1)
        placeholder = Snapshot(estado="desconocido", texto="")  # lo que deja correr() tras un fallo
        decision = decidir(pais(cerrado=["closed for"]), placeholder, "closed for 2026")
        assert decision.tipo == "siembra"
        assert decision.estado == "cerrado"


class TestEvidencia:
    """D10: una apertura debe tener evidencia verificable (cita de la fuente)."""

    def test_cita_alrededor_de_la_keyword(self) -> None:
        relleno = "palabra " * 30
        texto = f"{relleno}la temporada esta ABIERTA desde hoy {relleno}"
        cita = evidencia(texto, ["abierta"])
        assert "ABIERTA" in cita
        assert len(cita) < 170  # ventana corta, no la pagina entera

    def test_sin_match_devuelve_vacio(self) -> None:
        assert evidencia("nada relevante aqui", ["abierta"]) == ""

    def test_prueba_las_keywords_en_orden(self) -> None:
        cita = evidencia("texto con open", ["closed", "open"])
        assert "open" in cita

    def test_keyword_cercana_al_inicio_no_se_corta_mal(self) -> None:
        cita = evidencia("open desde el primer caracter", ["open"])
        assert cita.startswith("open")


class TestClasificarContexto:
    """D10: una noticia no equivale a convocatoria abierta."""

    def test_keyword_con_contexto_cercano_cuenta(self) -> None:
        irlanda = pais(abierto=["open"], contexto="chile")
        texto = "programa entre irlanda y chile: applications are open"
        assert clasificar(texto, irlanda) == "abierto"

    def test_keyword_lejos_del_contexto_no_cuenta(self) -> None:
        # noticia de otro programa: "open" a mas de una ventana de "chile"
        irlanda = pais(abierto=["open"], contexto="chile")
        lejania = "palabra " * 60  # ~360 chars
        texto = f"chile y su embajada publican datos. {lejania} the germany scheme is open"
        assert clasificar(texto, irlanda) == "desconocido"

    def test_sin_contexto_configurado_comporta_como_antes(self) -> None:
        australia = pais(abierto=["open"])
        assert clasificar("the germany scheme is open", australia) == "abierto"


class TestDecidirFallo:
    def test_primer_fallo_se_ignora(self) -> None:
        assert decidir_fallo(0).tipo == "ignore"

    def test_segundo_fallo_consecutivo_notifica(self) -> None:
        decision = decidir_fallo(1)
        assert decision.tipo == "fuente_inaccesible"
