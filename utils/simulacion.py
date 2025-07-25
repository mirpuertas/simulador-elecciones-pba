from __future__ import annotations
import pandas as pd
import numpy as np
from scipy.spatial.distance import cdist
from utils.reglas_electorales import repartir_bancas
from typing import Callable, Mapping

__all__ = ["simular_eleccion", "resumen", "medoid"]

def simular_eleccion(dirichlet_pesos, data, participacion, votos_validos_pct, phi=None):
    """Simula una elección usando distribuciones Dirichlet"""
    
    if phi is not None:
        P_prov = np.random.dirichlet(dirichlet_pesos)

    def simular_y_repartir(secciones_camara):
        filas = []
        for sec, cargos in secciones_camara.items():
            pad = data['padron_real'][sec]
            votos_validos = int(pad * participacion * votos_validos_pct)

            if phi is None:
                prop = np.random.dirichlet(dirichlet_pesos)
            else:
                prop = np.random.dirichlet(P_prov * phi)

            votos = (prop * votos_validos).astype(int)
            for lista, v in zip(data['listas_politicas'], votos):
                filas.append({"seccion": sec, "lista": lista,
                              "votos": v, "cargos": cargos})
        df = pd.DataFrame(filas)
        return repartir_bancas(df)

    dip = simular_y_repartir(data['secciones_diputados'])
    sen = simular_y_repartir(data['secciones_senadores'])
    return dip, sen


def medoid(df):
    """Calcula el medoid de las simulaciones"""
    df = df.fillna(0)
    if df.empty:
        raise ValueError("DataFrame vacío")
    D = cdist(df.values, df.values, metric="cityblock")
    idx = np.nanargmin(D.sum(axis=1))
    return df.iloc[idx].astype(int)


def resumen(df):
    """Genera resumen estadístico de las simulaciones"""
    return pd.DataFrame({
        "Media": df.mean(),
        "P5": df.quantile(0.05),
        "P95": df.quantile(0.95),
        "Bancas": medoid(df).astype(int)
    }).round(2)
