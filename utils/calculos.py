import pandas as pd
from typing import Dict
from collections.abc import Callable
from utils.cuociente import repartir_bancas

__all__ = [
    "calcular_determinista",
    "calcular_determinista_por_seccion",
    "agregar_bancas_no_renovadas"
]

def _generar_filas_para_camara(
    secciones: Dict[str, int],
    padron_real: Dict[str, int],
    creencias_seccion: Callable[[str], Dict[str, int]],
    participacion: float,
    votos_validos_pct: float
) -> list[dict]:
    """
    Genera las filas de datos que servirán de entrada a ``repartir_bancas``.

    Parameters
    ----------
    secciones : dict[str, int]
        Mapeo *sección → cantidad de cargos* que se ponen en juego
        en la cámara correspondiente.
    padron_real : dict[str, int]
        Mapeo *sección → cantidad de electores* (padrón habilitado).
    creencias_seccion : Callable[[str], dict[str, int]]
        Función que, dado el nombre de la sección, devuelve las
        creencias porcentuales ``alianza → %`` (0‒100) **ya filtradas**
        para las alianzas que compiten allí.
    participacion : float
        Proporción de participación sobre el padrón habilitado
        (valor entre 0 y 1).
    votos_validos_pct : float
        Proporción de votos válidos sobre los sufragios emitidos
        (valor entre 0 y 1).

    Returns
    -------
    list[dict]
        Cada elemento tiene las claves:
        ``{"seccion", "lista", "votos", "cargos"}``.
    """
    filas = []
    for seccion, cargos in secciones.items():
        pad = padron_real[seccion]
        validos = int(pad * participacion * votos_validos_pct)
        for alianza, pct in creencias_seccion(seccion).items():
            filas.append(
                dict(seccion=seccion, lista=alianza,
                     votos=int(validos * pct / 100), cargos=cargos)
            )
        if not filas:
            filas.append(dict(seccion=seccion, lista="Ninguna", votos=0, cargos=cargos))
    return filas

def _normalizar_creencias_para_seccion(
    creencias: Dict[str, int], 
    seccion: str, 
    secciones_x_alianza: Dict[str, set]
) -> Dict[str, float]:
    """
    Re‑escala las creencias para que sumen 100 % en la sección indicada.

    Las alianzas que no compiten allí se descartan antes de normalizar.

    Parameters
    ----------
    creencias : dict[str, int]
        Intención de voto global «alianza → %» antes de filtrar por sección.
    seccion : str
        Sección electoral a la que se aplica el filtro.
    secciones_x_alianza : dict[str, set[str]]
        Mapeo «alianza → conjunto de secciones donde efectivamente compite».

    Returns
    -------
    dict[str, float]
        Intención de voto re‑normalizada (0‒100) sólo para las
        alianzas válidas en la sección.  Devuelve un diccionario
        vacío si ninguna alianza compite allí.
    """
    alianzas_validas = {
        a: pct for a, pct in creencias.items()
        if a in secciones_x_alianza and seccion in secciones_x_alianza[a]
    }
    total = sum(alianzas_validas.values())
    if total == 0:
        return {}
    return {a: 100 * v / total for a, v in alianzas_validas.items()}


def calcular_determinista(
    creencias_global: Dict[str, int],
    secciones_diputados: Dict[str, int],
    secciones_senadores: Dict[str, int],
    padron_real: Dict[str, int],
    secciones_x_alianza: Dict[str, set],
    participacion: float,
    votos_validos_pct: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Asigna bancas suponiendo **una única** intención de voto para
    todas las secciones.

    Parameters
    ----------
    creencias_global : dict[str, int]
        Intención de voto global «alianza → %».
    secciones_diputados, secciones_senadores : dict[str, int]
        Mapeo «sección → cargos a elegir» para cada cámara.
    padron_real : dict[str, int]
        Padrón habilitado por sección.
    secciones_x_alianza : dict[str, set[str]]
        Conjunto de secciones en las que compite cada alianza.
    participacion : float
        Proporción de participación (0‒1).
    votos_validos_pct : float
        Proporción de votos válidos (0‒1).

    Returns
    -------
    (pandas.DataFrame, pandas.DataFrame)
        DataFrames *diputados* y *senadores* con las columnas:
        ``["seccion", "lista", "votos", "bancas"]``.
    """
    def _creencias_func(seccion):
        return _normalizar_creencias_para_seccion(
            creencias_global, seccion, secciones_x_alianza
        )

    filas_dip = _generar_filas_para_camara(
        secciones_diputados, padron_real, _creencias_func, participacion, votos_validos_pct
    )
    filas_sen = _generar_filas_para_camara(
        secciones_senadores, padron_real, _creencias_func, participacion, votos_validos_pct
    )

    dip = repartir_bancas(pd.DataFrame(filas_dip))
    sen = repartir_bancas(pd.DataFrame(filas_sen))

    return dip, sen


def calcular_determinista_por_seccion(
    creencias_por_seccion: Dict[str, Dict[str, int]],
    secciones_diputados: Dict[str, int],
    secciones_senadores: Dict[str, int],
    padron_real: Dict[str, int],
    secciones_x_alianza: Dict[str, set],
    participacion: float,
    votos_validos_pct: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Asigna bancas permitiendo valores distintos de intención de voto
    en cada sección.

    Si una sección no está presente en ``creencias_por_seccion``,
    se usa la clave ``"global"`` como valor por defecto.

    Parameters
    ----------
    creencias_por_seccion : dict[str, dict[str, int]]
        Mapeo «sección → (alianza → %)».  Debe incluir la clave
        ``"global"``.
    secciones_diputados, secciones_senadores : dict[str, int]
        Mapeo «sección → cargos a elegir» para cada cámara.
    padron_real : dict[str, int]
        Padrón habilitado por sección.
    secciones_x_alianza : dict[str, set[str]]
        Conjunto de secciones en las que compite cada alianza.
    participacion : float
        Proporción de participación (0‒1).
    votos_validos_pct : float
        Proporción de votos válidos (0‒1).

    Returns
    -------
    (pandas.DataFrame, pandas.DataFrame)
        DataFrames *diputados* y *senadores* con las columnas:
        ``["seccion", "lista", "votos", "bancas"]``.
    """
    def _creencias_func(seccion):
        base = creencias_por_seccion.get(seccion, creencias_por_seccion["global"])
        return _normalizar_creencias_para_seccion(
            base, seccion, secciones_x_alianza
        )

    filas_dip = _generar_filas_para_camara(
        secciones_diputados, padron_real, _creencias_func, participacion, votos_validos_pct
    )
    filas_sen = _generar_filas_para_camara(
        secciones_senadores, padron_real, _creencias_func, participacion, votos_validos_pct
    )

    dip = repartir_bancas(pd.DataFrame(filas_dip))
    sen = repartir_bancas(pd.DataFrame(filas_sen))

    return dip, sen


def agregar_bancas_no_renovadas(
    nuevas: pd.Series, 
    no_renuevan: Dict[str, Dict[str, int]]
) -> pd.Series:
    """
    Suma las bancas que no se disputan a las recién asignadas.

    Parameters
    ----------
    nuevas : pandas.Series
        Serie «alianza → bancas nuevas».
    no_renuevan : dict[str, dict[str, int]]
        Mapeo «sección → (alianza → bancas que no concluyen mandato)».

    Returns
    -------
    pandas.Series
        Banca total por alianza (*nuevas + no renovadas*),
        siempre de tipo ``int``.
    """
    total = nuevas.copy()
    for _, dic in no_renuevan.items():
        for alianza, n in dic.items():
            total[alianza] = total.get(alianza, 0) + n
    return total.fillna(0).astype(int) 