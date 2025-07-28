from __future__ import annotations

import streamlit as st
import geopandas as gpd

from utils import loader, calculos
from ui import (
    configurar_sidebar, 
    configurar_intenciones_voto, 
    renderizar_boton_ejecutar, 
    mostrar_resultados
)

# ------ Configuración de Streamlit ------
st.set_page_config(
    page_title="Simulador Electoral PBA",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""<h1 style='text-align:center'>🗳️ Simulador Electoral PBA</h1>""", unsafe_allow_html=True)

# ------ Carga de datos: el año vigente se lee de config.ini por defecto. ------
@st.cache_data(show_spinner=False)
def build_context(alianzas_visibles: list[str]):
    """Construye el contexto completo con todos los datos necesarios."""
    congreso = loader.cargar_congreso(None)

    padron = congreso.obtener_padron()
    bancas = congreso.obtener_bancas_por_seccion()["a_elegir_2025"]

    return dict(
        CONGRESO=congreso, 
        PADRON_REAL=padron,
        SECCIONES_DIPUTADOS=bancas["diputados"],
        SECCIONES_SENADORES=bancas["senadores"],
        COLORES_PARTIDOS=congreso.obtener_colores_alianzas(),
        SECCIONES_X_ALIANZA=congreso.obtener_secciones_por_alianza(),
        BANCAS_NO_RENUEVAN=congreso.obtener_bancas_no_disputadas()
    )

@st.cache_data(show_spinner=False)
def load_secciones_geojson(path: str = "data/secciones-electorales-pba.geojson") -> gpd.GeoDataFrame | None:
    """Lee el GeoJSON de secciones"""
    try:
        return gpd.read_file(path)
    except Exception as exc:  # pragma: no cover – solo falla en tiempo de ejecución
        st.error(f"Error cargando GeoJSON: {exc}")
        return None

# ------ Configuración inicial ------
ALIANZAS_RECOMENDADAS = [
    "Alianza La Libertad Avanza",
    "Alianza Fuerza Patria",
    "Alianza Somos Buenos Aires",
    "Alianza FIT-U",
]

ctx_tmp = build_context([])  # TEMPORAL → usar build_context sólo para obtener estructura y padrón
SECCIONES_X_ALIANZA = ctx_tmp["SECCIONES_X_ALIANZA"]
PADRON_REAL = ctx_tmp["PADRON_REAL"]

ALIANZAS_GLOBALES = [
    a for a, secciones in SECCIONES_X_ALIANZA.items()
    if len(secciones) >= 1
]

GDF_SECCIONES = load_secciones_geojson()  # Cargar geodata

# ------ Interfaz de usuario ------

# Configurar sidebar y obtener alianzas visibles
alianzas_visibles, configuracion = configurar_sidebar(
    ALIANZAS_GLOBALES, 
    ALIANZAS_RECOMENDADAS, 
    SECCIONES_X_ALIANZA, 
    PADRON_REAL
)

ctx = build_context(alianzas_visibles)  # Construir contexto con alianzas seleccionadas

# Configurar intenciones de voto
creencias_global, creencias_por_seccion = configurar_intenciones_voto(
    alianzas_visibles,
    configuracion['cfg_seccion'],
    ctx["PADRON_REAL"],
    ctx["SECCIONES_X_ALIANZA"]
)

# Extraer configuración
cfg_seccion = configuracion['cfg_seccion']
participacion = configuracion['participacion']
votos_validos_pct = configuracion['votos_validos_pct']

# Validar total
total_pct = sum(creencias_global.values())

# Renderizar botón de ejecución
if renderizar_boton_ejecutar(total_pct):
    
    # Cálculo determinista
    if cfg_seccion and creencias_por_seccion:
        dip_nuevas, sen_nuevas = calculos.calcular_determinista_por_seccion(
            creencias_por_seccion,
            ctx["SECCIONES_DIPUTADOS"],
            ctx["SECCIONES_SENADORES"],
            ctx["PADRON_REAL"],
            ctx["SECCIONES_X_ALIANZA"],
            participacion,
            votos_validos_pct,
        )
    else:
        dip_nuevas, sen_nuevas = calculos.calcular_determinista(
            creencias_global,
            ctx["SECCIONES_DIPUTADOS"],
            ctx["SECCIONES_SENADORES"],
            ctx["PADRON_REAL"],
            ctx["SECCIONES_X_ALIANZA"],
            participacion,
            votos_validos_pct,
        )

    # Suma bancas no renovadas
    dip_final = calculos.agregar_bancas_no_renovadas(
        dip_nuevas.groupby("lista").bancas.sum(), 
        ctx["BANCAS_NO_RENUEVAN"]["diputados"]
    )
    sen_final = calculos.agregar_bancas_no_renovadas(
        sen_nuevas.groupby("lista").bancas.sum(), 
        ctx["BANCAS_NO_RENUEVAN"]["senadores"]
    )

    # Guardar en session_state
    st.session_state.resultados = {
        "dip_final": dip_final,
        "sen_final": sen_final,
        "dip_nuevas": dip_nuevas,
        "sen_nuevas": sen_nuevas,
        "participacion": participacion,
        "votos_validos_pct": votos_validos_pct
    }

# ------ Mostrar resultados ------
if "resultados" in st.session_state:
    res = st.session_state.resultados
    
    mostrar_resultados(
        res["dip_final"], 
        res["sen_final"], 
        ctx=ctx,
        gdf_secciones=GDF_SECCIONES,
        detalles_por_seccion=(res["dip_nuevas"], res["sen_nuevas"])
    )