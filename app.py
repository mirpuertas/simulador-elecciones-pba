"""
Simulador Electoral PBA — versión modular
========================================
Este script Streamlit carga toda la lógica electoral a partir de dos archivos
por año (JSON + CSV), sin hard‑codear valores específicos de 2025.  Bastará con
copiar `estructura_congreso_completa_<anio>.json` y
`congreso_composicion_inicial_<anio>.csv` dentro de `data/` y cambiar
`año_vigente` en `config.ini` o pasar el año por la UI.

Requiere los módulos:
- utils.congreso   (manejador de datos electorales y composición actual)
- utils.loader     (selección del par JSON/CSV según el año)
- utils.calculos   (algoritmos de reparto, simulación, resumen, etc.)

Para mantener el ejemplo breve, las funciones de cálculo importadas​
(`repartir_bancas`, `simular_eleccion`, `resumen`, `medoid`)
están en `utils/calculos.py` tal como las usabas antes.
"""

from __future__ import annotations  # noqa: D401, I001

# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

import geopandas as gpd
from utils import reglas_electorales, loader, simulacion, plots

# ---------------------------------------------------------------------------
# Carga de datos: el año vigente se lee de config.ini por defecto.
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def build_context(alianzas_visibles: list[str]):
    congreso = loader.cargar_congreso(None)

    padron = congreso.obtener_padron()
    bancas = congreso.obtener_bancas_por_seccion()["a_elegir_2025"]

    return dict(
        CONGRESO=congreso, 
        PADRON_REAL=padron,
        SECCIONES_DIPUTADOS=bancas["diputados"],
        SECCIONES_SENADORES=bancas["senadores"],
        DATA_SIM={
            "secciones_diputados": bancas["diputados"],
            "secciones_senadores": bancas["senadores"],
            "padron_real": padron,
            "listas_politicas": alianzas_visibles
        },
        COLORES_PARTIDOS=congreso.obtener_colores_alianzas(),
        SECCIONES_X_ALIANZA=congreso.obtener_secciones_por_alianza(),
        BANCAS_NO_RENUEVAN=congreso.obtener_bancas_no_disputadas()
    )

ALIANZAS_RECOMENDADAS = [
    "Alianza La Libertad Avanza",
    "Alianza Fuerza Patria",
    "Alianza Somos Buenos Aires",
    "Alianza FIT-U",
]

# TEMPORAL → usar build_context solo para obtener estructura y padron
ctx_tmp = build_context([])  # sin alianzas visibles
SECCIONES_X_ALIANZA = ctx_tmp["SECCIONES_X_ALIANZA"]
PADRON_REAL = ctx_tmp["PADRON_REAL"]


ALIANZAS_GLOBALES = [
    a for a, secciones in SECCIONES_X_ALIANZA.items()
    if len(secciones) >= 1
]

# Interfaz de selección
ALIANZAS_VISIBLES = st.sidebar.multiselect(
    "🧮 Alianzas visibles (nivel general)",
    options=ALIANZAS_GLOBALES,
    default=[a for a in ALIANZAS_RECOMENDADAS if a in ALIANZAS_GLOBALES]
)

for alianza in ALIANZAS_VISIBLES:
    secciones = SECCIONES_X_ALIANZA.get(alianza, set())
    if set(secciones) != set(PADRON_REAL.keys()):
        st.sidebar.info(f"⚠️ '{alianza}' no compite en todas las secciones.")

# Ahora sí: construir el contexto con lo que eligió el usuario
ctx = build_context(ALIANZAS_VISIBLES)

# Desempaquetar las variables
PADRON_REAL          = ctx["PADRON_REAL"]
SECCIONES_DIPUTADOS  = ctx["SECCIONES_DIPUTADOS"]
SECCIONES_SENADORES  = ctx["SECCIONES_SENADORES"]
DATA_SIM             = ctx["DATA_SIM"]
COLORES_PARTIDOS     = ctx["COLORES_PARTIDOS"]
SECCIONES_X_ALIANZA  = ctx["SECCIONES_X_ALIANZA"]
BANCAS_NO_RENUEVAN   = ctx["BANCAS_NO_RENUEVAN"]

# ---------------------------------------------------------------------------
# Funciones auxiliares
# ---------------------------------------------------------------------------
def load_secciones_geojson(path: str = "data/secciones-electorales-pba.geojson") -> gpd.GeoDataFrame | None:
    """Lee el GeoJSON de secciones"""
    try:
        return gpd.read_file(path)
    except Exception as exc:  # pragma: no cover – solo falla en tiempo de ejecución
        st.error(f"Error cargando GeoJSON: {exc}")
        return None


def sumar_no_renovados(nuevas: pd.Series, no_renuevan: dict[str, dict[str, int]]) -> pd.Series:
    """Suma al resultado (Series) las bancas que no se disputan en 2025."""
    total = nuevas.copy()
    for _, dic in no_renuevan.items():
        for alianza, n in dic.items():
            total[alianza] = total.get(alianza, 0) + n
    return total.fillna(0).astype(int)


@st.cache_data(show_spinner=False)
def load_geo():  # Separado para que @cache_data no tope con argumentos mutables
    return load_secciones_geojson()

GDF_SECCIONES = load_geo()

# ---------------------------------------------------------------------------
# Funciones que dependen de Streamlit (se definen al final para claridad)
# ---------------------------------------------------------------------------
def _filas_para_camara(secciones, creencias_seccion, participacion, votos_validos):
    filas = []
    for seccion, cargos in secciones.items():
        pad = PADRON_REAL[seccion]
        validos = int(pad * participacion * votos_validos)
        for alianza, pct in creencias_seccion(seccion).items():
            filas.append(
                dict(seccion=seccion, lista=alianza,
                     votos=int(validos*pct/100), cargos=cargos)
            )
    return filas

def calcular_determinista(
    creencias: dict[str, int],
    participacion: float,
    votos_validos_pct: float
):
    """Reparte bancas de forma determinista (sin secciones específicas)."""
    
    # Esta función aplica siempre la misma creencia global, filtrada por sección
    def creencias_func(seccion):
        return normalizar_creencias_para_seccion(creencias, seccion)

    filas_dip = _filas_para_camara(SECCIONES_DIPUTADOS, creencias_func, participacion, votos_validos_pct)
    filas_sen = _filas_para_camara(SECCIONES_SENADORES, creencias_func, participacion, votos_validos_pct)

    dip = reglas_electorales.repartir_bancas(pd.DataFrame(filas_dip))
    sen = reglas_electorales.repartir_bancas(pd.DataFrame(filas_sen))

    return dip, sen

def calcular_determinista_por_seccion(
    creencias_sec: dict[str, dict[str, int]],
    participacion: float,
    votos_validos_pct: float
):
    """Reparte bancas usando porcentajes distintos por sección."""
    
    # Esta función aplica una creencia específica si está definida, o la global si no
    def creencias_func(seccion):
        base = creencias_sec.get(seccion, creencias_sec["global"])
        return normalizar_creencias_para_seccion(base, seccion)

    filas_dip = _filas_para_camara(SECCIONES_DIPUTADOS, creencias_func, participacion, votos_validos_pct)
    filas_sen = _filas_para_camara(SECCIONES_SENADORES, creencias_func, participacion, votos_validos_pct)

    dip = reglas_electorales.repartir_bancas(pd.DataFrame(filas_dip))
    sen = reglas_electorales.repartir_bancas(pd.DataFrame(filas_sen))

    return dip, sen


def normalizar_creencias_para_seccion(creencias: dict[str, int], seccion: str) -> dict[str, float]:
    """Devuelve un nuevo diccionario de creencias normalizado a 100% para la sección indicada,
    descartando las alianzas que no compiten en esa sección."""
    alianzas_validas = {
        a: pct for a, pct in creencias.items()
        if a in SECCIONES_X_ALIANZA and seccion in SECCIONES_X_ALIANZA[a]
    }
    total = sum(alianzas_validas.values())
    if total == 0:
        return {}
    return {a: 100 * v / total for a, v in alianzas_validas.items()}

def mostrar_resultados(
    dip_final: pd.Series,
    sen_final: pd.Series,
    *,
    modo: str,
    tablas: tuple[pd.DataFrame, pd.DataFrame] | None = None,
    distribuciones: tuple[pd.DataFrame, pd.DataFrame] | None = None,
    detalles_por_seccion: tuple[pd.DataFrame, pd.DataFrame] | None = None,
):
    """Pinta métricas, tablas y gráficos en tabs según el modo."""
    tabs = ["🏛️ Parlamentos", "📋 Detalles"]
    if modo == "simulacion":
        tabs.insert(0, "📈 Distribuciones")
        tabs.insert(0, "📊 Bancas Ganadas")
    else:
        tabs.insert(0, "📊 Bancas Ganadas")

    tab_objs = st.tabs(tabs)

    # --- Bancas Ganadas (nuevo primer tab) ---
    with tab_objs[0] if modo == "determinista" else tab_objs[1]:
        st.subheader("📊 Bancas ganadas por sección")
        
        if detalles_por_seccion is not None:
            dip_nuevas, sen_nuevas = detalles_por_seccion
            
            # Tablas de bancas ganadas por sección
            dip_ganadas = dip_nuevas.groupby(["seccion", "lista"]).bancas.sum().unstack(fill_value=0)
            sen_ganadas = sen_nuevas.groupby(["seccion", "lista"]).bancas.sum().unstack(fill_value=0)
            
            col_table1, col_table2 = st.columns(2)
            with col_table1:
                st.markdown("#### Diputados - Bancas ganadas")
                st.dataframe(dip_ganadas, use_container_width=True)
                
            with col_table2:
                st.markdown("#### Senadores - Bancas ganadas")
                st.dataframe(sen_ganadas, use_container_width=True)
            
            # CSS para mapas
            st.markdown("""
            <style>
            .stPlotlyChart, .stPyplot {
                height: 600px !important;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # --- Mapas de bancas ganadas ---
            if GDF_SECCIONES is not None and not dip_ganadas.empty:
                st.markdown("### 🗺️ Mapas de bancas ganadas por alianza")
                
                # Crear tabs para los tipos de mapas
                tab_ganadas, tab_ganador_sec = st.tabs(["📊 Por alianza", "🏆 Quién ganó"])
                
                with tab_ganadas:
                    st.markdown("#### Bancas ganadas por alianza")
                    
                    col_dip, col_sen = st.columns(2)
                    
                    with col_dip:
                        st.markdown("**Diputados**")
                        alianzas_disponibles_dip = list(dip_ganadas.columns)
                        alianza_dip = st.selectbox(
                            "Elegí alianza (Diputados):",
                            alianzas_disponibles_dip,
                            index=0,
                            key="dip_ganadas"
                        )
                        
                        fig_dip = plots.crear_mapa_bancas_ganadas(
                            GDF_SECCIONES, dip_ganadas, alianza_dip,
                            f"Bancas ganadas - {alianza_dip} (Diputados)"
                        )
                        st.pyplot(fig_dip, use_container_width=True)
                        plt.close(fig_dip)
                    
                    with col_sen:
                        st.markdown("**Senadores**")
                        alianzas_disponibles_sen = list(sen_ganadas.columns)
                        alianza_sen = st.selectbox(
                            "Elegí alianza (Senadores):",
                            alianzas_disponibles_sen,
                            index=0,
                            key="sen_ganadas"
                        )
                        
                        fig_sen = plots.crear_mapa_bancas_ganadas(
                            GDF_SECCIONES, sen_ganadas, alianza_sen,
                            f"Bancas ganadas - {alianza_sen} (Senadores)"
                        )
                        st.pyplot(fig_sen, use_container_width=True)
                        plt.close(fig_sen)
                
                with tab_ganador_sec:
                    st.markdown("#### Quién ganó más bancas por sección")
                    
                    col_dip_g, col_sen_g = st.columns(2)
                    
                    with col_dip_g:
                        st.markdown("**Diputados - Quién ganó más bancas**")
                        fig_dip_ganador = plots.crear_mapa_ganadores(
                            GDF_SECCIONES, dip_ganadas, COLORES_PARTIDOS,
                            "Partido con más bancas nuevas - Diputados"
                        )
                        st.pyplot(fig_dip_ganador, use_container_width=True)
                        plt.close(fig_dip_ganador)
                    
                    with col_sen_g:
                        st.markdown("**Senadores - Quién ganó más bancas**")
                        fig_sen_ganador = plots.crear_mapa_ganadores(
                            GDF_SECCIONES, sen_ganadas, COLORES_PARTIDOS,
                            "Partido con más bancas nuevas - Senadores"
                        )
                        st.pyplot(fig_sen_ganador, use_container_width=True)
                        plt.close(fig_sen_ganador)
        


    # --- Distribuciones (solo simulación) ---
    if modo == "simulacion":
        dip_df, sen_df = distribuciones or (None, None)
        with tab_objs[0]:  # primer tab para simulación
            st.subheader("📈 Distribuciones – Diputados")
            plots.plot_distribucion(dip_df)
            st.subheader("📈 Distribuciones – Senadores")
            plots.plot_distribucion(sen_df)
        parlamento_idx = 2
        detalles_idx = 3
    else:
        parlamento_idx = 1
        detalles_idx = 2

    # --- Parlamentos ---
    with tab_objs[parlamento_idx]:
        st.subheader("🏛️ Parlamento provincial 2025 – 2027")
        c1, c2 = st.columns(2)
        with c1:
            fig1 = plots.crear_parlamento(dip_final, "Diputados", COLORES_PARTIDOS)
            if fig1:
                st.pyplot(fig1)
        with c2:
            fig2 = plots.crear_parlamento(sen_final, "Senadores", COLORES_PARTIDOS)
            if fig2:
                st.pyplot(fig2)

    # --- Detalles ---
    with tab_objs[detalles_idx]:
        # Primero el resumen de bancas (movido desde el primer tab)
        st.subheader("📊 Resumen de bancas")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### Diputados")
            if tablas:
                st.dataframe(tablas[0])
            else:
                st.dataframe(dip_final.rename("Bancas"))
        with col2:
            st.markdown("#### Senadores")
            if tablas:
                st.dataframe(tablas[1])
            else:
                st.dataframe(sen_final.rename("Bancas"))
        
        st.markdown("---")  # Separador visual
        
        st.subheader("📋 Parámetros y métricas")
        # Obtener participación y votos válidos desde session_state si están disponibles
        part = st.session_state.get("resultados", {}).get("participacion", participacion)
        votos_val = st.session_state.get("resultados", {}).get("votos_validos_pct", votos_validos_pct)
        
        col_param1, col_param2, col_param3 = st.columns(3)
        with col_param1:
            st.metric("Padrón total", f"{sum(PADRON_REAL.values()):,}")
        with col_param2:
            st.metric("Participación", f"{part:.1%}")
        with col_param3:
            st.metric("Votos válidos", f"{votos_val:.1%}")
        
        # Solo mostrar tablas de diferencias sin mapas
        if detalles_por_seccion is not None:
            dip_nuevas, sen_nuevas = detalles_por_seccion
           
            def diferencia_por_seccion(df_nuevo, camara):
                def map_alianzas(dic):
                    m = ctx_tmp["CONGRESO"].partido_a_alianza
                    return {m.get(p.strip().upper(), p): n for p, n in dic.items()}

                # 1) Nuevas bancas 2025
                nuevas = (df_nuevo
                        .groupby(["seccion", "lista"]).bancas
                        .sum()
                        .unstack(fill_value=0))

                # 2) Bancas NO renovadas (seguras S)
                seguras = (pd.DataFrame({sec: map_alianzas(dic)
                                        for sec, dic in BANCAS_NO_RENUEVAN[camara].items()})
                        .T.reindex_like(nuevas)       # <-- sin fill_value
                        .fillna(0)                    # <-- rellena vacíos
                        .astype(int))

                # 3) Composición completa ANTES de la elección
                viejas = (pd.DataFrame({sec: map_alianzas(dic)
                                        for sec, dic in ctx_tmp["CONGRESO"]
                                        .composicion_actual[camara].items()})
                        .T.reindex_like(nuevas)        # idem
                        .fillna(0)
                        .astype(int))

                # 4) Totales nuevos y variación
                nuevas_totales = nuevas + seguras           # S + N
                return (nuevas_totales - viejas).astype(int)  # (S+N) − (S+U)


            dip_cambio = diferencia_por_seccion(dip_nuevas, "diputados")
            sen_cambio = diferencia_por_seccion(sen_nuevas, "senadores")

            # --- Tablas de diferencias ---
            st.markdown("### 📊 Ganancia/Pérdida por Sección")
            
            col_table1, col_table2 = st.columns(2)
            with col_table1:
                st.markdown("#### Cámara de Diputados")
                st.dataframe(dip_cambio.style.format("{:+}"), use_container_width=True)
            
            with col_table2:
                st.markdown("#### Senado Provincial")
                st.dataframe(sen_cambio.style.format("{:+}"), use_container_width=True)
            
            # --- Mapas de diferencias ---
            if GDF_SECCIONES is not None and not dip_cambio.empty:
                st.markdown("### 🗺️ Mapas de diferencias por alianza")
                
                # Crear tabs para los dos tipos de mapas
                tab_dif, tab_ganador = st.tabs(["📊 Diferencias", "🏆 Quién ganó"])
                
                with tab_dif:
                    st.markdown("#### Mapas de diferencias de bancas")
                    
                    col_dip, col_sen = st.columns(2)
                    
                    with col_dip:
                        st.markdown("**Diputados**")
                        alianzas_disponibles = list(dip_cambio.columns)
                        alianza_dip = st.selectbox(
                            "Elegí alianza (Diputados):",
                            alianzas_disponibles,
                            index=0,
                            key="dip_diferencias_detalles"
                        )
                        
                        fig_dip = plots.crear_mapa_diferencias_estatico(
                            GDF_SECCIONES, dip_cambio, alianza_dip,
                            f"Diferencia de bancas - {alianza_dip}"
                        )
                        st.pyplot(fig_dip, use_container_width=True)
                        plt.close(fig_dip)
                    
                    with col_sen:
                        st.markdown("**Senadores**")
                        alianzas_disponibles_sen = list(sen_cambio.columns)
                        alianza_sen = st.selectbox(
                            "Elegí alianza (Senadores):",
                            alianzas_disponibles_sen,
                            index=0,
                            key="sen_diferencias_detalles"
                        )
                        
                        fig_sen = plots.crear_mapa_diferencias_estatico(
                            GDF_SECCIONES, sen_cambio, alianza_sen,
                            f"Diferencia de bancas - {alianza_sen}"
                        )
                        st.pyplot(fig_sen, use_container_width=True)
                        plt.close(fig_sen)
                
                with tab_ganador:
                    st.markdown("#### Mapas de partidos ganadores por sección")
                    
                    # Calcular bancas totales (nuevas + no renovadas)
                    def calcular_bancas_totales(df_nuevas, bancas_no_renuevan, camara):
                        def mapear_alianzas(dic):
                            mapeo = ctx_tmp["CONGRESO"].partido_a_alianza
                            salida = {}
                            for partido, n in dic.items():
                                alianza = mapeo.get(partido.strip().upper(), partido)
                                salida[alianza] = salida.get(alianza, 0) + n
                            return salida

                        nuevas = df_nuevas.groupby(["seccion", "lista"]).bancas.sum().unstack(fill_value=0)
                        viejas = pd.DataFrame({
                            sec: mapear_alianzas(dic)
                            for sec, dic in bancas_no_renuevan[camara].items()
                        }).T.fillna(0).astype(int)
                        viejas = viejas.reindex(index=nuevas.index, columns=nuevas.columns, fill_value=0)
                        return (nuevas + viejas).astype(int)
                    
                    dip_totales = calcular_bancas_totales(dip_nuevas, BANCAS_NO_RENUEVAN, "diputados")
                    sen_totales = calcular_bancas_totales(sen_nuevas, BANCAS_NO_RENUEVAN, "senadores")
                    
                    col_dip_g, col_sen_g = st.columns(2)
                    
                    with col_dip_g:
                        st.markdown("**Diputados - Quién ganó más bancas**")
                        fig_dip_ganador = plots.crear_mapa_ganadores(
                            GDF_SECCIONES, dip_totales, COLORES_PARTIDOS,
                            "Partido con más bancas - Diputados"
                        )
                        st.pyplot(fig_dip_ganador, use_container_width=True)
                        plt.close(fig_dip_ganador)
                    
                    with col_sen_g:
                        st.markdown("**Senadores - Quién ganó más bancas**")
                        fig_sen_ganador = plots.crear_mapa_ganadores(
                            GDF_SECCIONES, sen_totales, COLORES_PARTIDOS,
                            "Partido con más bancas - Senadores"
                        )
                        st.pyplot(fig_sen_ganador, use_container_width=True)
                        plt.close(fig_sen_ganador)





# ---------------------------------------------------------------------------
# Streamlit – layout básico
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Simulador Electoral PBA",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""<h1 style='text-align:center'>🗳️ Simulador Electoral PBA</h1>""", unsafe_allow_html=True)

# ---------------- Sidebar -----------------
sidebar = st.sidebar
sidebar.header("⚙️ Configuración de Simulación")

### A REVISAR EL MODO AVANZADO EN UNA VERSIÓN POSTERIOR A LA PUBLICACIÓN ###

# modo = sidebar.radio(
#     "Tipo de cálculo",
#     ("📊 Básico (Determinista)", "🎲 Avanzado (Simulación)"),
# )

modo = sidebar.radio(
    "Tipo de cálculo",
    ("📊 Básico"),
)
es_deterministico = modo.startswith("📊")

if es_deterministico:
    cfg_seccion = sidebar.checkbox("🗺️ Configuración por sección")
else:
    cfg_seccion = False

sidebar.subheader("Parámetros electorales")
participacion = sidebar.slider("Participación (%)", 40, 85, 60) / 100
votos_validos_pct = sidebar.slider("Votos válidos (%)", 80, 98, 90) / 100


sidebar.subheader("Intención de voto (%)")

sliders = {}
cols = sidebar.columns(2)

for i, alianza in enumerate(ALIANZAS_VISIBLES):
    col = cols[i % 2]
    sliders[alianza] = col.slider(
        alianza,
        min_value=0,
        max_value=80,
        value=25,
        step=1,
        key=f"global_slider_{alianza}"
    )

# Total y validación
total_pct = sum(sliders.values())
if total_pct != 100:
    sidebar.warning(f"Total {total_pct}% (debe sumar 100)")
else:
    sidebar.success("Total 100% ✅")

creencias_global = sliders

creencias_por_seccion: dict[str, dict[str, int]] = {"global": creencias_global}

if cfg_seccion:
    sidebar.markdown("---")
    sidebar.subheader("📍 Por sección")

    selecciones = sidebar.multiselect(
        "Secciones a personalizar",
        list(PADRON_REAL.keys()),
    )

    for sec in selecciones:
        alianzas_en_seccion = [
            a for a, secs in SECCIONES_X_ALIANZA.items()
            if sec in secs          # todas las que compiten en esta sección
        ]
        # Opcional: mantener primero las visibles globales
        alianzas_en_seccion.sort(key=lambda x: x not in ALIANZAS_VISIBLES)
        with sidebar.expander(sec):
            sliders = {}
            cols = st.columns(2)
            for i, alianza in enumerate(alianzas_en_seccion):
                col = cols[i % 2]
                sliders[alianza] = col.slider(
                    alianza, 0, 100, creencias_global.get(alianza, 0),
                    key=f"{alianza}_{sec}"
                )
            suma = sum(sliders.values())
            if suma != 100:
                st.warning(f"{suma}% (≠100)")
            creencias_por_seccion[sec] = sliders

# ---------------- Mostrar datos de entrada -----------------

# ---------------- Botón ejecutar -----------------
# Solo si modo simulación
if not es_deterministico:
    sidebar.subheader("🎲 Parámetros de simulación")
    n_sim = sidebar.slider("Simulaciones", 100, 2000, 1000)
    alpha_scale = sidebar.slider("Alpha scale", 10, 100, 25)
    phi_hier = sidebar.slider("Phi", 10, 100, 50)

btn_txt = "🚀 Ejecutar cálculo" if es_deterministico else "🚀 Ejecutar simulación"
if sidebar.button(btn_txt, type="primary"):

    if total_pct != 100:
        st.error("❌ Los porcentajes deben sumar 100%.")
        st.stop()

    # --- Cálculo determinista ---
    if es_deterministico:
        if cfg_seccion and creencias_por_seccion:
            dip_nuevas, sen_nuevas = calcular_determinista_por_seccion(
                creencias_por_seccion,
                participacion,
                votos_validos_pct,
            )
        else:
            dip_nuevas, sen_nuevas = calcular_determinista(
                creencias_global,
                participacion,
                votos_validos_pct,
            )

        # Suma bancas no renovadas
        dip_final = sumar_no_renovados(dip_nuevas.groupby("lista").bancas.sum(), BANCAS_NO_RENUEVAN["diputados"])
        sen_final = sumar_no_renovados(sen_nuevas.groupby("lista").bancas.sum(), BANCAS_NO_RENUEVAN["senadores"])

        # Guardar en session_state
        st.session_state.resultados = {
            "dip_final": dip_final,
            "sen_final": sen_final,
            "modo": "determinista",
            "dip_nuevas": dip_nuevas,
            "sen_nuevas": sen_nuevas,
            "participacion": participacion,
            "votos_validos_pct": votos_validos_pct
        }

    # --- Simulación Monte Carlo ---
    else:
        pesos_dir = np.array(list(creencias_global.values())) * alpha_scale / 100
        #--------NORMALIZACIÓN--------
        # Evita que los pesos sean cero o negativos, lo cual causaría errores en Dir
        eps = 1e-3
        pesos_dir = np.maximum(eps, pesos_dir)
        #-----------------------------
        dip_sim, sen_sim = [], []
        prog = st.progress(0)
        txt = st.empty()
        
        for i in range(n_sim):
            d, s = simulacion.simular_eleccion(dirichlet_pesos= pesos_dir, data=DATA_SIM, participacion=participacion, votos_validos_pct=votos_validos_pct, phi=phi_hier)
            dip_sim.append(d)
            sen_sim.append(s)
            if i % 10 == 0:
                prog.progress((i + 1) / n_sim)
                txt.text(f"Simulación {i+1}/{n_sim}")

        prog.empty(); txt.empty()

        dip_df = pd.DataFrame([df.groupby("lista").bancas.sum() for df in dip_sim]).reindex(columns=ALIANZAS_VISIBLES).fillna(0)
        sen_df = pd.DataFrame([df.groupby("lista").bancas.sum() for df in sen_sim]).reindex(columns=ALIANZAS_VISIBLES).fillna(0)



        #-------------------------
        dip_medoid = simulacion.medoid(dip_df)
        sen_medoid = simulacion.medoid(sen_df)

        # Obtengo el índice de la fila medoid
        idx_medoid_dip = dip_df.reset_index(drop=True).apply(lambda row: (row == dip_medoid).all(), axis=1).idxmax()
        dip_nuevas = dip_sim[idx_medoid_dip]  

        idx_medoid_sen = sen_df.reset_index(drop=True).apply(lambda row: (row == sen_medoid).all(), axis=1).idxmax()
        sen_nuevas = sen_sim[idx_medoid_sen]
        
       
        #-------------------------


        dip_final = sumar_no_renovados(dip_medoid, BANCAS_NO_RENUEVAN["diputados"])
        sen_final = sumar_no_renovados(sen_medoid, BANCAS_NO_RENUEVAN["senadores"])

        # Resúmenes estadísticos
        tbl_dip, tbl_sen = simulacion.resumen(dip_df), simulacion.resumen(sen_df)

        # Guardar en session_state
        st.session_state.resultados = {
            "dip_final": dip_final,
            "sen_final": sen_final,
            "modo": "simulacion",
            "tablas": (tbl_dip, tbl_sen),
            "distribuciones": (dip_df, sen_df),
            "dip_nuevas": dip_nuevas,
            "sen_nuevas": sen_nuevas,
            "participacion": participacion,
            "votos_validos_pct": votos_validos_pct
        }


# Mostrar resultados desde session_state
if "resultados" in st.session_state:
    res = st.session_state.resultados
    
    if res["modo"] == "determinista":
        mostrar_resultados(
            res["dip_final"], 
            res["sen_final"], 
            modo="determinista",
            detalles_por_seccion=(res["dip_nuevas"], res["sen_nuevas"])
        )
    else:
        mostrar_resultados(
            res["dip_final"], 
            res["sen_final"], 
            modo="simulacion", 
            tablas=res["tablas"], 
            distribuciones=res["distribuciones"], 
            detalles_por_seccion=(res["dip_nuevas"], res["sen_nuevas"])
        )