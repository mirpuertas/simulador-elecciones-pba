from __future__ import annotations

import pandas as pd
import streamlit as st
from utils import plots

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import geopandas as gpd


def configurar_sidebar(alianzas_globales: list[str], alianzas_recomendadas: list[str], 
                      secciones_x_alianza: dict, padron_real: dict) -> tuple[list[str], dict]:
    """Configura el sidebar y retorna las alianzas visibles y la configuración."""
    sidebar = st.sidebar
    sidebar.header("⚙️ Configuración Electoral")

    # Selección de alianzas visibles
    alianzas_visibles = sidebar.multiselect(
        "🧮 Alianzas visibles",
        options=alianzas_globales,
        default=[a for a in alianzas_recomendadas if a in alianzas_globales]
    )

    # Advertencias por alianzas que no compiten en todas las secciones
    for alianza in alianzas_visibles:
        secciones = secciones_x_alianza.get(alianza, set())
        if set(secciones) != set(padron_real.keys()):
            sidebar.info(f"⚠️ '{alianza}' no compite en todas las secciones.")

    # Configuración por sección
    cfg_seccion = sidebar.checkbox("🗺️ Configuración por sección")

    # Parámetros electorales
    sidebar.subheader("Parámetros electorales")
    participacion = sidebar.slider("Participación (%)", 40, 85, 60) / 100
    votos_validos_pct = sidebar.slider("Votos válidos (%)", 80, 98, 90) / 100

    return alianzas_visibles, {
        'cfg_seccion': cfg_seccion,
        'participacion': participacion,
        'votos_validos_pct': votos_validos_pct
    }


def configurar_intenciones_voto(alianzas_visibles: list[str], cfg_seccion: bool, 
                               padron_real: dict, secciones_x_alianza: dict) -> tuple[dict, dict]:
    """Configura las intenciones de voto globales y por sección."""
    sidebar = st.sidebar
    sidebar.subheader("Intención de voto (%)")

    # Sliders globales
    sliders = {}
    cols = sidebar.columns(2)

    for i, alianza in enumerate(alianzas_visibles):
        col = cols[i % 2]
        sliders[alianza] = col.slider(
            alianza,
            min_value=0,
            max_value=80,
            value=25,
            step=1,
            key=f"global_slider_{alianza}"
        )

    # Validación del total
    total_pct = sum(sliders.values())
    if total_pct != 100:
        sidebar.warning(f"Total {total_pct}% (debe sumar 100)")
    else:
        sidebar.success("Total 100% ✅")

    creencias_global = sliders
    creencias_por_seccion = {"global": creencias_global}

    # Configuración por sección
    if cfg_seccion:
        sidebar.markdown("---")
        sidebar.subheader("📍 Por sección")

        selecciones = sidebar.multiselect(
            "Secciones a personalizar",
            list(padron_real.keys()),
        )

        for sec in selecciones:
            alianzas_en_seccion = [
                a for a, secs in secciones_x_alianza.items()
                if sec in secs
            ]
            alianzas_en_seccion.sort(key=lambda x: x not in alianzas_visibles)
            
            with sidebar.expander(sec):
                sliders_sec = {}
                cols = st.columns(2)
                for i, alianza in enumerate(alianzas_en_seccion):
                    col = cols[i % 2]
                    sliders_sec[alianza] = col.slider(
                        alianza, 0, 100, creencias_global.get(alianza, 0),
                        key=f"{alianza}_{sec}"
                    )
                suma = sum(sliders_sec.values())
                if suma != 100:
                    st.warning(f"{suma}% (≠100)")
                creencias_por_seccion[sec] = sliders_sec

    return creencias_global, creencias_por_seccion


def renderizar_boton_ejecutar(total_pct: int) -> bool:
    """Renderiza el botón de ejecución y retorna si fue presionado."""
    sidebar = st.sidebar
    
    if sidebar.button("🚀 Ejecutar cálculo", type="primary"):
        if total_pct != 100:
            st.error("❌ Los porcentajes deben sumar 100%.")
            st.stop()
        return True
    
    return False


def mostrar_resultados(
    dip_final: pd.Series,
    sen_final: pd.Series,
    *,
    ctx: dict,
    gdf_secciones: gpd.GeoDataFrame | None = None,
    detalles_por_seccion: tuple[pd.DataFrame, pd.DataFrame] | None = None,
):
    """Pinta métricas, tablas y gráficos en tabs."""
    # Extraer variables del contexto
    colores_partidos = ctx["COLORES_PARTIDOS"]
    bancas_no_renuevan = ctx["BANCAS_NO_RENUEVAN"]
    participacion = st.session_state.get("resultados", {}).get("participacion", 0.6)
    votos_validos_pct = st.session_state.get("resultados", {}).get("votos_validos_pct", 0.9)
    padron_real = ctx["PADRON_REAL"]
    
    tabs = ["📊 Bancas Ganadas", "🏛️ Parlamentos", "📋 Detalles"]
    tab_objs = st.tabs(tabs)

    # Bancas Ganadas
    with tab_objs[0]:
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
            
            # Mapas de bancas ganadas
            if gdf_secciones is not None and not dip_ganadas.empty:
                _renderizar_mapas_bancas_ganadas(gdf_secciones, dip_ganadas, sen_ganadas, colores_partidos)

    # Parlamentos
    with tab_objs[1]:
        st.subheader("🏛️ Parlamento provincial 2025 – 2027")
        c1, c2 = st.columns(2)
        with c1:
            fig1 = plots.crear_parlamento(dip_final, "Diputados", colores_partidos)
            if fig1:
                st.pyplot(fig1)
        with c2:
            fig2 = plots.crear_parlamento(sen_final, "Senadores", colores_partidos)
            if fig2:
                st.pyplot(fig2)

    # Detalles
    with tab_objs[2]:
        _renderizar_tab_detalles(dip_final, sen_final, padron_real, participacion, 
                                votos_validos_pct, detalles_por_seccion, ctx, gdf_secciones)


def _renderizar_mapas_bancas_ganadas(gdf_secciones: gpd.GeoDataFrame, dip_ganadas: pd.DataFrame, 
                                   sen_ganadas: pd.DataFrame, colores_partidos: dict):
    """Renderiza los mapas de bancas ganadas."""
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
            
            fig_dip = plots.mapa_bancas_ganadas(
                gdf_secciones, dip_ganadas, alianza_dip,
                f"Bancas ganadas - {alianza_dip} (Diputados)"
            )
            st.pyplot(fig_dip, use_container_width=True)
        
        with col_sen:
            st.markdown("**Senadores**")
            alianzas_disponibles_sen = list(sen_ganadas.columns)
            alianza_sen = st.selectbox(
                "Elegí alianza (Senadores):",
                alianzas_disponibles_sen,
                index=0,
                key="sen_ganadas"
            )
            
            fig_sen = plots.mapa_bancas_ganadas(
                gdf_secciones, sen_ganadas, alianza_sen,
                f"Bancas ganadas - {alianza_sen} (Senadores)"
            )
            st.pyplot(fig_sen, use_container_width=True)
    
    with tab_ganador_sec:
        st.markdown("#### Quién ganó más bancas por sección")
        
        col_dip_g, col_sen_g = st.columns(2)
        
        with col_dip_g:
            st.markdown("**Diputados - Quién ganó más bancas**")
            fig_dip_ganador = plots.mapa_ganadores(
                gdf_secciones, dip_ganadas, colores_partidos,
                "Partido con más bancas nuevas - Diputados"
            )
            st.pyplot(fig_dip_ganador, use_container_width=True)
        
        with col_sen_g:
            st.markdown("**Senadores - Quién ganó más bancas**")
            fig_sen_ganador = plots.mapa_ganadores(
                gdf_secciones, sen_ganadas, colores_partidos,
                "Partido con más bancas nuevas - Senadores"
            )
            st.pyplot(fig_sen_ganador, use_container_width=True)


def _renderizar_tab_detalles(dip_final: pd.Series, sen_final: pd.Series,
                           padron_real: dict, participacion: float, votos_validos_pct: float,
                           detalles_por_seccion: tuple[pd.DataFrame, pd.DataFrame] | None,
                           ctx: dict, gdf_secciones: gpd.GeoDataFrame | None):
    """Renderiza el tab de detalles."""

    st.subheader("📊 Resumen de bancas")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Diputados")
        st.dataframe(dip_final.rename("Bancas"))
    with col2:
        st.markdown("#### Senadores")
        st.dataframe(sen_final.rename("Bancas"))
    
    st.markdown("---")
   
    st.subheader("📋 Parámetros y métricas")
    col_param1, col_param2, col_param3 = st.columns(3)
    with col_param1:
        st.metric("Padrón total", f"{sum(padron_real.values()):,}")
    with col_param2:
        st.metric("Participación", f"{participacion:.1%}")
    with col_param3:
        st.metric("Votos válidos", f"{votos_validos_pct:.1%}")
    
    if detalles_por_seccion is not None:
        _renderizar_diferencias_por_seccion(detalles_por_seccion, ctx, gdf_secciones)


def _renderizar_diferencias_por_seccion(detalles_por_seccion: tuple[pd.DataFrame, pd.DataFrame],
                                       ctx: dict, gdf_secciones: gpd.GeoDataFrame | None):
    """Renderiza las diferencias por sección."""
    dip_nuevas, sen_nuevas = detalles_por_seccion
    bancas_no_renuevan = ctx["BANCAS_NO_RENUEVAN"]
    colores_partidos = ctx["COLORES_PARTIDOS"]
    
    def diferencia_por_seccion(df_nuevo, camara):
        def map_alianzas(dic):
            m = ctx["CONGRESO"].partido_a_alianza
            return {m.get(p.strip().upper(), p): n for p, n in dic.items()}

        # 1) Nuevas bancas
        nuevas = (df_nuevo
                .groupby(["seccion", "lista"]).bancas
                .sum()
                .unstack(fill_value=0))

        # 2) Bancas NO renovadas (seguras S)
        seguras = (pd.DataFrame({sec: map_alianzas(dic)
                                for sec, dic in bancas_no_renuevan[camara].items()})
                .T.reindex_like(nuevas)
                .fillna(0)
                .astype(int))

        # 3) Composición completa ANTES de la elección
        viejas = (pd.DataFrame({sec: map_alianzas(dic)
                                for sec, dic in ctx["CONGRESO"]
                                .composicion_actual[camara].items()})
                .T.reindex_like(nuevas)
                .fillna(0)
                .astype(int))

        # 4) Totales nuevos y variación
        nuevas_totales = nuevas + seguras
        return (nuevas_totales - viejas).astype(int)

    dip_cambio = diferencia_por_seccion(dip_nuevas, "diputados")
    sen_cambio = diferencia_por_seccion(sen_nuevas, "senadores")

    # Tablas de diferencias
    st.markdown("### 📊 Ganancia/Pérdida por Sección")
    
    col_table1, col_table2 = st.columns(2)
    with col_table1:
        st.markdown("#### Cámara de Diputados")
        st.dataframe(dip_cambio.style.format("{:+}"), use_container_width=True)
    
    with col_table2:
        st.markdown("#### Senado Provincial")
        st.dataframe(sen_cambio.style.format("{:+}"), use_container_width=True)
    
    # Mapas de diferencias
    if gdf_secciones is not None and not dip_cambio.empty:
        _renderizar_mapas_diferencias(gdf_secciones, dip_cambio, sen_cambio, colores_partidos,
                                    dip_nuevas, sen_nuevas, bancas_no_renuevan, ctx)


def _renderizar_mapas_diferencias(gdf_secciones: gpd.GeoDataFrame, dip_cambio: pd.DataFrame,
                                sen_cambio: pd.DataFrame, colores_partidos: dict,
                                dip_nuevas: pd.DataFrame, sen_nuevas: pd.DataFrame,
                                bancas_no_renuevan: dict, ctx: dict):
    """Renderiza los mapas de diferencias."""
    st.markdown("### 🗺️ Mapas de diferencias por alianza")

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
            
            fig_dip = plots.mapa_diferencias_estatico(
                gdf_secciones, dip_cambio, alianza_dip,
                f"Diferencia de bancas - {alianza_dip}"
            )
            st.pyplot(fig_dip, use_container_width=True)
        
        with col_sen:
            st.markdown("**Senadores**")
            alianzas_disponibles_sen = list(sen_cambio.columns)
            alianza_sen = st.selectbox(
                "Elegí alianza (Senadores):",
                alianzas_disponibles_sen,
                index=0,
                key="sen_diferencias_detalles"
            )
            
            fig_sen = plots.mapa_diferencias_estatico(
                gdf_secciones, sen_cambio, alianza_sen,
                f"Diferencia de bancas - {alianza_sen}"
            )
            st.pyplot(fig_sen, use_container_width=True)
    
    with tab_ganador:
        st.markdown("#### Mapas de partidos ganadores por sección")
        
        # Calcular bancas totales (nuevas + no renovadas)
        def calcular_bancas_totales(df_nuevas, bancas_no_renuevan, camara):
            def mapear_alianzas(dic):
                mapeo = ctx["CONGRESO"].partido_a_alianza
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
        
        dip_totales = calcular_bancas_totales(dip_nuevas, bancas_no_renuevan, "diputados")
        sen_totales = calcular_bancas_totales(sen_nuevas, bancas_no_renuevan, "senadores")
        
        col_dip_g, col_sen_g = st.columns(2)
        
        with col_dip_g:
            st.markdown("**Diputados - Quién ganó más bancas**")
            fig_dip_ganador = plots.mapa_ganadores(
                gdf_secciones, dip_totales, colores_partidos,
                "Partido con más bancas - Diputados"
            )
            st.pyplot(fig_dip_ganador, use_container_width=True)
        
        with col_sen_g:
            st.markdown("**Senadores - Quién ganó más bancas**")
            fig_sen_ganador = plots.mapa_ganadores(
                gdf_secciones, sen_totales, colores_partidos,
                "Partido con más bancas - Senadores"
            )
            st.pyplot(fig_sen_ganador, use_container_width=True)
