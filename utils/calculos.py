from __future__ import annotations
import pandas as pd
from typing import Callable, Dict
from utils.cuociente import repartir_bancas

__all__ = [
    "calcular_determinista",
    "calcular_determinista_por_seccion",
    "agregar_bancas_no_renovadas"
]

def _generar_filas_para_camara(
    secciones: Dict[str, int],
    padron_real: Dict[str, int],
    creencias_seccion: Callable[[str], dict[str, int]],
    participacion: float,
    votos_validos: float
) -> list[dict]:
    """
    Genera las filas de datos para una cámara específica.
    
    Args:
        secciones: Diccionario con sección -> cantidad de cargos
        padron_real: Diccionario con sección -> cantidad de electores
        creencias_seccion: Función que recibe una sección y devuelve dict alianza -> porcentaje
        participacion: Porcentaje de participación (0.0 a 1.0)
        votos_validos: Porcentaje de votos válidos (0.0 a 1.0)
    
    Returns:
        Lista de diccionarios con los datos para repartir bancas
    """
    filas = []
    for seccion, cargos in secciones.items():
        pad = padron_real[seccion]
        validos = int(pad * participacion * votos_validos)
        for alianza, pct in creencias_seccion(seccion).items():
            filas.append(
                dict(seccion=seccion, lista=alianza,
                     votos=int(validos * pct / 100), cargos=cargos)
            )
    return filas

def _normalizar_creencias_para_seccion(
    creencias: Dict[str, int], 
    seccion: str, 
    secciones_x_alianza: Dict[str, set]
) -> Dict[str, float]:
    """
    Normaliza las creencias a 100% para una sección específica,
    descartando las alianzas que no compiten en esa sección.
    
    Args:
        creencias: Diccionario alianza -> porcentaje de intención de voto
        seccion: Nombre de la sección electoral
        secciones_x_alianza: Diccionario alianza -> set de secciones donde compite
    
    Returns:
        Diccionario normalizado alianza -> porcentaje (suma 100%)
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
    Reparte bancas de forma determinista usando la misma creencia global para todas las secciones.
    
    Args:
        creencias_global: Diccionario alianza -> porcentaje de intención de voto
        secciones_diputados: Diccionario sección -> bancas de diputados a elegir
        secciones_senadores: Diccionario sección -> bancas de senadores a elegir
        padron_real: Diccionario sección -> cantidad de electores
        secciones_x_alianza: Diccionario alianza -> set de secciones donde compite
        participacion: Porcentaje de participación (0.0 a 1.0)
        votos_validos_pct: Porcentaje de votos válidos (0.0 a 1.0)
    
    Returns:
        Tupla con (DataFrame diputados, DataFrame senadores) con bancas asignadas
    """
    
    # Función que aplica la creencia global filtrada por sección
    def creencias_func(seccion):
        return _normalizar_creencias_para_seccion(
            creencias_global, seccion, secciones_x_alianza
        )

    filas_dip = _generar_filas_para_camara(
        secciones_diputados, padron_real, creencias_func, participacion, votos_validos_pct
    )
    filas_sen = _generar_filas_para_camara(
        secciones_senadores, padron_real, creencias_func, participacion, votos_validos_pct
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
    Reparte bancas usando porcentajes distintos por sección.
    
    Args:
        creencias_por_seccion: Diccionario con sección -> {alianza -> porcentaje}
                              Debe incluir una clave "global" como fallback
        secciones_diputados: Diccionario sección -> bancas de diputados a elegir
        secciones_senadores: Diccionario sección -> bancas de senadores a elegir
        padron_real: Diccionario sección -> cantidad de electores
        secciones_x_alianza: Diccionario alianza -> set de secciones donde compite
        participacion: Porcentaje de participación (0.0 a 1.0)
        votos_validos_pct: Porcentaje de votos válidos (0.0 a 1.0)
    
    Returns:
        Tupla con (DataFrame diputados, DataFrame senadores) con bancas asignadas
    """
    
    # Función que aplica creencia específica si existe, o la global como fallback
    def creencias_func(seccion):
        base = creencias_por_seccion.get(seccion, creencias_por_seccion["global"])
        return _normalizar_creencias_para_seccion(
            base, seccion, secciones_x_alianza
        )

    filas_dip = _generar_filas_para_camara(
        secciones_diputados, padron_real, creencias_func, participacion, votos_validos_pct
    )
    filas_sen = _generar_filas_para_camara(
        secciones_senadores, padron_real, creencias_func, participacion, votos_validos_pct
    )

    dip = repartir_bancas(pd.DataFrame(filas_dip))
    sen = repartir_bancas(pd.DataFrame(filas_sen))

    return dip, sen


def agregar_bancas_no_renovadas(
    nuevas: pd.Series, 
    no_renuevan: Dict[str, Dict[str, int]]
) -> pd.Series:
    """
    Suma las bancas que no se disputan a las bancas nuevas asignadas.
    
    Args:
        nuevas: Series con alianza -> bancas nuevas asignadas
        no_renuevan: Diccionario con sección -> {alianza -> bancas que no se renuevan}
    
    Returns:
        Series con el total de bancas (nuevas + no renovadas)
    """
    total = nuevas.copy()
    for _, dic in no_renuevan.items():
        for alianza, n in dic.items():
            total[alianza] = total.get(alianza, 0) + n
    return total.fillna(0).astype(int) 