import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.spatial.distance import cdist
from scipy.stats import gaussian_kde
import plotly.express as px
import plotly.graph_objects as go
from matplotlib.patches import Patch
import poli_sci_kit.plot as pk

# Configuración de página
st.set_page_config(
    page_title="Simulador Electoral PBA 2025",
    page_icon="🗳️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        color: #1f4e79;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# Datos y configuración inicial
@st.cache_data
def load_data():
    """Carga los datos necesarios para la simulación"""
    
    # Datos de secciones y bancas
    secciones_diputados = {
        "Capital": 6,
        "Segunda": 11,
        "Tercera": 18,
        "Sexta": 11    
    }

    secciones_senadores = {
        "Primera": 8,
        "Cuarta": 7,
        "Quinta": 5,
        "Séptima": 3
    }

    # Padrón real por sección
    padron_real = {
        "Capital": 576_691,
        "Primera": 4_732_831,
        "Segunda": 649_465,
        "Tercera": 4_637_863,
        "Cuarta": 540_354,
        "Quinta": 1_290_948, 
        "Sexta": 652_077, 
        "Séptima": 281_130
    }

    # Listas políticas
    listas_politicas = [
        "Alianza La Libertad Avanza",
        "Fuerza Patria",
        "Somos Buenos Aires",
        "Avanza Libertad",
        "FIT-U"
    ]

    # Bancas no renovadas
    senado_no_elegido = {
        "Capital": {"UxP":2, "PRO": 1},
        "Segunda": {"UxP":2, "PRO": 2, "Unión renovación y fe": 1},
        "Tercera": {"UxP":5, "PRO": 1, "LLA": 3},
        "Sexta": {"UxP":2, "PRO": 1, "UCR": 1, "Unión renovación y fe": 2}
    }

    diputados_no_elegidos = {
        "Primera": {"UxP":7, "PRO": 2, "LLA": 4, "Unión renovación y fe": 2, "UNIÓN Y LIBERTAD": 1},
        "Cuarta": {"UxP":5, "PRO": 2, "Coalición cívica": 1, "Unión renovación y fe": 1, "UCR + Cambio Federal": 2, "UNIÓN Y LIBERTAD": 2},
        "Quinta": {"UxP":4, "UCR + Cambio Federal": 1, "Acuerdo cívico - UCR + Gen": 1, "Coalición cívica": 1, "LLA": 3, "UNIÓN Y LIBERTAD": 1},
        "Séptima": {"UxP":2, "PRO": 1, "LLA": 1, "UCR + Cambio Federal": 1, "UNIÓN Y LIBERTAD": 1},
    }

    # Mapeo de alianzas
    alianzas_2023_a_2025 = {
        "PRO": "Alianza La Libertad Avanza",
        "LLA": "Alianza La Libertad Avanza",
        "UxP": "Fuerza Patria",
        "UCR": "Somos Buenos Aires",
        "Cambio Federal": "Somos Buenos Aires",
        "Coalición cívica": "Somos Buenos Aires",
        "UCR + Cambio Federal": "Somos Buenos Aires",
        "Unión renovación y fe": "Unión renovación y fe",
        "UNIÓN Y LIBERTAD": "UNIÓN Y LIBERTAD",
        "FIT-U": "FIT-U",
        "Acuerdo cívico - UCR + Gen": "Somos Buenos Aires"
    }

    return {
        'secciones_diputados': secciones_diputados,
        'secciones_senadores': secciones_senadores,
        'padron_real': padron_real,
        'listas_politicas': listas_politicas,
        'senado_no_elegido': senado_no_elegido,
        'diputados_no_elegidos': diputados_no_elegidos,
        'alianzas_2023_a_2025': alianzas_2023_a_2025
    }

def repartir_bancas(df):
    """Implementa el sistema D'Hondt para reparto de bancas"""
    out = []

    for seccion, grupo in df.groupby("seccion"):
        total_votos = grupo["votos"].sum()
        cargos      = grupo["cargos"].iloc[0]
        cuociente   = max(1, total_votos // cargos)

        grupo = grupo.copy()
        grupo["enteros"] = grupo["votos"] // cuociente
        grupo["residuo"] = grupo["votos"] %  cuociente
        grupo["bancas"]  = grupo["enteros"]

        # Restos solo entre listas con ≥1 cuociente
        faltan = cargos - grupo["bancas"].sum()
        if faltan:
            elig = grupo[grupo["enteros"] > 0]
            if not elig.empty:
                idx = (elig.sort_values(["residuo", "votos"],
                                        ascending=False)
                             .head(faltan).index)
                grupo.loc[idx, "bancas"] += 1

        # Art. 110: nadie alcanzó cuociente
        if grupo["bancas"].sum() == 0:
            q = cuociente
            while grupo["bancas"].sum() == 0:
                q = max(1, q // 2)
                grupo["enteros"] = grupo["votos"] // q
                grupo["residuo"] = grupo["votos"] %  q
                grupo["bancas"]  = grupo["enteros"]

                faltan = cargos - grupo["bancas"].sum()
                if faltan:
                    elig = grupo[grupo["enteros"] > 0]
                    if not elig.empty:
                        idx = (elig.sort_values(["residuo", "votos"],
                                                ascending=False)
                                       .head(faltan).index)
                        grupo.loc[idx, "bancas"] += 1

        # Completar con la lista más votada
        faltan = cargos - grupo["bancas"].sum()
        if faltan:
            top = grupo["votos"].idxmax()
            grupo.loc[top, "bancas"] += faltan

        out.append(grupo[["seccion", "lista", "bancas"]])

    return pd.concat(out, ignore_index=True)

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

def calcular_determinista(creencias, data, participacion, votos_validos_pct):
    """Calcula reparto determinista de bancas"""
    
    # Diputados
    filas_dip = []
    for seccion, cargos in data['secciones_diputados'].items():
        pad = data['padron_real'][seccion]
        total_validos = int(pad * participacion * votos_validos_pct)
        for alianza, pct in creencias.items():
            votos = int(total_validos * pct / 100)
            filas_dip.append({"seccion": seccion, "lista": alianza, "votos": votos, "cargos": cargos})
    
    df_dip_det = pd.DataFrame(filas_dip)
    dip_bancas_det = repartir_bancas(df_dip_det)
    
    # Senadores  
    filas_sen = []
    for seccion, cargos in data['secciones_senadores'].items():
        pad = data['padron_real'][seccion]
        total_validos = int(pad * participacion * votos_validos_pct)
        for alianza, pct in creencias.items():
            votos = int(total_validos * pct / 100)
            filas_sen.append({"seccion": seccion, "lista": alianza, "votos": votos, "cargos": cargos})
    
    df_sen_det = pd.DataFrame(filas_sen)
    sen_bancas_det = repartir_bancas(df_sen_det)
    
    return dip_bancas_det, sen_bancas_det

def mapear_a_alianzas(diccionario, secciones_dict):
    """Mapea partidos históricos a alianzas actuales"""
    nuevo = {}
    for seccion, partidos in secciones_dict.items():
        nuevo[seccion] = {}
        for partido, bancas in partidos.items():
            alianza = diccionario.get(partido, partido)
            nuevo[seccion][alianza] = nuevo[seccion].get(alianza, 0) + bancas
    return nuevo

def crear_diagrama_parlamento(bancas_series, titulo, colores_dict):
    """Crea un diagrama de parlamento usando poli-sci-kit"""
    
    # Limpiar figuras anteriores para evitar conflictos
    plt.close('all')
    
    # Filtrar solo partidos con bancas > 0
    bancas_filtradas = bancas_series[bancas_series > 0].sort_values(ascending=False)
    
    if bancas_filtradas.empty:
        st.warning(f"No hay datos para mostrar en {titulo}")
        return None
              
    colores_usados = [colores_dict.get(nombre, "#999999") for nombre in bancas_filtradas.index]
    
    # Crear figura sin ax predefinido para evitar conflicto con seaborn
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        pk.parliament(
            allocations=bancas_filtradas.tolist(),
            labels=bancas_filtradas.index.tolist(),
            colors=colores_usados,
            style="semicircle",
            num_rows=5 if "diputado" in titulo.lower() else 3,
            marker_size=180,
            legend=True,
            axis=ax
        )
        
        ax.set_title(titulo, fontsize=16, fontweight='bold', pad=20)
        
        total_bancas = bancas_filtradas.sum()
        ax.text(0, 0, str(total_bancas), ha='center', va='center',
                fontsize=20, fontweight='bold', color='gray', alpha=0.6)
        
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1),
                  ncol=3, frameon=False)
        
        return fig
    except Exception as e:
        st.error(f"Error creando diagrama de parlamento para {titulo}: {e}")
        return None

# Cargar datos
data = load_data()

# Header principal
st.markdown('<h1 class="main-header">🗳️ Simulador Electoral PBA 2025</h1>', unsafe_allow_html=True)

# Sidebar con controles
st.sidebar.header("⚙️ Configuración de Simulación")

# Modo de cálculo
modo = st.sidebar.radio(
    "Tipo de Cálculo",
    ["📊 Básico (Determinista)", "🎲 Avanzado (Simulación)"],
    help="Básico: Cálculo directo con porcentajes fijos. Avanzado: Simulación Monte Carlo con incertidumbre."
)

es_deterministico = modo.startswith("📊")

# Parámetros de simulación
st.sidebar.subheader("Parámetros Electorales")
participacion = st.sidebar.slider("Participación Electoral (%)", 40, 85, 60) / 100
votos_validos_pct = st.sidebar.slider("Votos Válidos (%)", 80, 98, 90) / 100

# Porcentajes de voto por partido
st.sidebar.subheader("Intención de Voto (%)")

# Usar columnas para mejor layout
col1, col2 = st.sidebar.columns(2)
with col1:
    lla_pct = st.slider("LLA", 0, 60, 36, key="lla")
    fp_pct = st.slider("FP", 0, 60, 35, key="fp")
    
with col2:
    sba_pct = st.slider("SBA", 0, 40, 15, key="sba") 
    al_pct = st.slider("AL", 0, 30, 10, key="al")

fit_pct = st.sidebar.slider("FIT-U", 0, 20, 4, key="fit")

# Control de suma 100%
total = lla_pct + fp_pct + sba_pct + al_pct + fit_pct
if total != 100:
    st.sidebar.warning(f"⚠️ Total: {total}% (debe sumar 100%)")
else:
    st.sidebar.success("✅ Total: 100%")

# Parámetros solo para modo avanzado
if not es_deterministico:
    st.sidebar.subheader("Parámetros de Simulación")
    n_simulaciones = st.sidebar.slider("Número de Simulaciones", 100, 2000, 1000)
    alpha_scale = st.sidebar.slider("Escala Alpha (concentración)", 10, 100, 25)
    phi_jerarquico = st.sidebar.slider("Phi Jerárquico", 10, 100, 50)

# Definir colores para los partidos
colores_partidos = {
    "Alianza La Libertad Avanza": "#9400D3",
    "Fuerza Patria": "#0066CC", 
    "Somos Buenos Aires": "#FF8C00",
    "Avanza Libertad": "#FF1493",
    "FIT-U": "#DC143C",
    "Unión renovación y fe": "#9536BE",
    "UNIÓN Y LIBERTAD": "#A62ED9"
}

# Botón para ejecutar cálculo
boton_texto = "🚀 Ejecutar Cálculo" if es_deterministico else "🚀 Ejecutar Simulación"
if st.sidebar.button(boton_texto, type="primary"):
    
    # Validar suma 100%
    if total != 100:
        st.error(f"❌ Los porcentajes deben sumar 100%. Actual: {total}%")
        st.stop()
    
    # Preparar parámetros
    creencias = {
        "Alianza La Libertad Avanza": lla_pct,
        "Fuerza Patria": fp_pct,
        "Somos Buenos Aires": sba_pct,
        "Avanza Libertad": al_pct,
        "FIT-U": fit_pct
    }
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Mapear bancas no renovadas a alianzas
    senado_no_elegido_alianzas = mapear_a_alianzas(data['alianzas_2023_a_2025'], data['senado_no_elegido'])
    diputados_no_elegidos_alianzas = mapear_a_alianzas(data['alianzas_2023_a_2025'], data['diputados_no_elegidos'])
    
    def sumar_no_renovados(bancas_dict, no_elegido_dict):
        total = bancas_dict.copy()
        for seccion, dic in no_elegido_dict.items():
            for partido, n in dic.items():
                total[partido] = total.get(partido, 0) + n
        return pd.Series(total).fillna(0).astype(int)
    
    if es_deterministico:
        # MODO DETERMINISTA
        status_text.text("Calculando reparto determinista...")
        progress_bar.progress(0.5)
        
        dip_bancas_det, sen_bancas_det = calcular_determinista(creencias, data, participacion, votos_validos_pct)
        
        # Convertir a series para sumar bancas no renovadas
        dip_nuevas = dip_bancas_det.groupby("lista").bancas.sum()
        sen_nuevas = sen_bancas_det.groupby("lista").bancas.sum()
        
        diputados_2025 = sumar_no_renovados(dip_nuevas, diputados_no_elegidos_alianzas)
        senado_2025 = sumar_no_renovados(sen_nuevas, senado_no_elegido_alianzas)
        
        # Para el modo determinista, creamos tablas simples
        tbl_dip = pd.DataFrame({
            "Bancas": dip_nuevas.reindex(data['listas_politicas']).fillna(0).astype(int)
        })
        tbl_sen = pd.DataFrame({
            "Bancas": sen_nuevas.reindex(data['listas_politicas']).fillna(0).astype(int)
        })
        
        progress_bar.progress(1.0)
        es_simulacion = False
        
    else:
        # MODO SIMULACIÓN
        pesos_dirichlet = np.array(list(creencias.values())) * alpha_scale / 100
        
        status_text.text("Ejecutando simulaciones Monte Carlo...")
        np.random.seed(123)
        
        dip_acum, sen_acum = [], []
        for i in range(n_simulaciones):
            d, s = simular_eleccion(pesos_dirichlet, data, participacion, votos_validos_pct, phi=phi_jerarquico)
            dip_acum.append(d.groupby("lista").bancas.sum())
            sen_acum.append(s.groupby("lista").bancas.sum())
            progress_bar.progress((i + 1) / n_simulaciones)
        
        status_text.text("Procesando resultados...")
        
        # Procesar resultados
        dip_mc = pd.DataFrame(dip_acum).reindex(columns=data['listas_politicas']).fillna(0)
        sen_mc = pd.DataFrame(sen_acum).reindex(columns=data['listas_politicas']).fillna(0)
        
        # Calcular resúmenes
        tbl_dip = resumen(dip_mc)
        tbl_sen = resumen(sen_mc)
        
        dip_medoid = medoid(dip_mc)
        sen_medoid = medoid(sen_mc)
        
        diputados_2025 = sumar_no_renovados(dip_medoid, diputados_no_elegidos_alianzas)
        senado_2025 = sumar_no_renovados(sen_medoid, senado_no_elegido_alianzas)
        
        es_simulacion = True
    
    progress_bar.empty()
    status_text.empty()
    
    # === MOSTRAR RESULTADOS ===
    
    # Tabs para organizar resultados
    if es_deterministico:
        tab1, tab3, tab4 = st.tabs(["📊 Resumen", "🏛️ Parlamentos", "📋 Detalles"])
        tab2 = None  # No hay distribuciones en modo determinista
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Resumen", "📈 Distribuciones", "🏛️ Parlamentos", "📋 Detalles"])
    
    with tab1:
        titulo_resultados = "🎯 Resultados del Cálculo" if es_deterministico else "🎯 Resultados de la Simulación"
        st.subheader(titulo_resultados)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🏛️ Cámara de Diputados")
            if es_deterministico:
                st.dataframe(tbl_dip)
            else:
                st.dataframe(tbl_dip.style.format({'Media': '{:.1f}', 'P5': '{:.1f}', 'P95': '{:.1f}'}))
            
            # Composición final Diputados
            st.markdown("### 📊 Composición Final Diputados (2025-2027)")
            total_dip = diputados_2025.sum()
            for partido, bancas in diputados_2025.sort_values(ascending=False).items():
                if bancas > 0:
                    porcentaje = (bancas / total_dip) * 100
                    st.metric(
                        label=partido,
                        value=f"{bancas} bancas ({porcentaje:.1f}%)"
                    )
        
        with col2:
            st.markdown("### 🏛️ Senado Provincial")
            if es_deterministico:
                st.dataframe(tbl_sen)
            else:
                st.dataframe(tbl_sen.style.format({'Media': '{:.1f}', 'P5': '{:.1f}', 'P95': '{:.1f}'}))
            
            # Composición final Senado
            st.markdown("### 📊 Composición Final Senado (2025-2027)")
            total_sen = senado_2025.sum()
            for partido, bancas in senado_2025.sort_values(ascending=False).items():
                if bancas > 0:
                    porcentaje = (bancas / total_sen) * 100
                    st.metric(
                        label=partido,
                        value=f"{bancas} bancas ({porcentaje:.1f}%)"
                    )
    
    if tab2:  # Solo existe en modo simulación
        with tab2:
            st.subheader("📈 Distribuciones de Probabilidad")
            
            # Gráfico de distribuciones para Diputados
            fig_dip, ax_dip = plt.subplots(figsize=(12, 6))
            for partido in dip_mc.columns:
                datos = dip_mc[partido].values
                if datos.max() > 0:  # Solo mostrar partidos con votos
                    kde = gaussian_kde(datos, bw_method='scott')
                    xs = np.linspace(datos.min(), datos.max(), 400)
                    dens = kde(xs)
                    color = colores_partidos.get(partido, '#999999')
                    ax_dip.plot(xs, dens, label=partido, color=color, linewidth=2)
                    
                    p5, p95 = np.percentile(datos, [5, 95])
                    mask = (xs >= p5) & (xs <= p95)
                    ax_dip.fill_between(xs[mask], dens[mask], alpha=0.15, color=color)
            
            ax_dip.set_title(f"Distribución de Bancas - Diputados ({n_simulaciones} simulaciones)", fontsize=14)
            ax_dip.set_xlabel("Cantidad de bancas")
            ax_dip.set_ylabel("Densidad")
            ax_dip.legend()
            ax_dip.grid(True, alpha=0.3)
            st.pyplot(fig_dip)
            
            # Gráfico de distribuciones para Senadores
            fig_sen, ax_sen = plt.subplots(figsize=(12, 6))
            for partido in sen_mc.columns:
                datos = sen_mc[partido].values
                if datos.max() > 0:  # Solo mostrar partidos con votos
                    kde = gaussian_kde(datos, bw_method='scott')
                    xs = np.linspace(datos.min(), datos.max(), 400)
                    dens = kde(xs)
                    color = colores_partidos.get(partido, '#999999')
                    ax_sen.plot(xs, dens, label=partido, color=color, linewidth=2)
                    
                    p5, p95 = np.percentile(datos, [5, 95])
                    mask = (xs >= p5) & (xs <= p95)
                    ax_sen.fill_between(xs[mask], dens[mask], alpha=0.15, color=color)
            
            ax_sen.set_title(f"Distribución de Bancas - Senadores ({n_simulaciones} simulaciones)", fontsize=14)
            ax_sen.set_xlabel("Cantidad de bancas")
            ax_sen.set_ylabel("Densidad")
            ax_sen.legend()
            ax_sen.grid(True, alpha=0.3)
            st.pyplot(fig_sen)
            plt.clf()
            
    
    with tab3:
        st.subheader("🏛️ Diagramas de Parlamento")
        
        # Crear diagramas de parlamento
        fig_parlamento_dip = crear_diagrama_parlamento(
            diputados_2025, 
            "Cámara de Diputados PBA (2025-2027)",
            colores_partidos
        )
        
        fig_parlamento_sen = crear_diagrama_parlamento(
            senado_2025,
            "Senado Provincial PBA (2025-2027)", 
            colores_partidos
        )
        
        if fig_parlamento_dip:
            st.pyplot(fig_parlamento_dip)
        
        if fig_parlamento_sen:
            st.pyplot(fig_parlamento_sen)
    
    with tab4:
        st.subheader("📋 Detalles de la Simulación")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### ⚙️ Parámetros Utilizados")
            st.write(f"**Participación:** {participacion:.1%}")
            st.write(f"**Votos válidos:** {votos_validos_pct:.1%}")
            
            if not es_deterministico:  # Solo mostrar parámetros de simulación en modo avanzado
                st.write(f"**Simulaciones:** {n_simulaciones:,}")
                st.write(f"**Escala Alpha:** {alpha_scale}")
                st.write(f"**Phi Jerárquico:** {phi_jerarquico}")
            else:
                st.write("**Modo:** Cálculo determinista")
            
            st.markdown("### 🗳️ Intención de Voto")
            for partido in data['listas_politicas']:
                st.write(f"**{partido}:** {creencias[partido]:.1f}%")
        
        with col2:
            st.markdown("### 📊 Estadísticas Clave")
            
            # Total de electores
            total_padron = sum(data['padron_real'].values())
            votantes_estimados = int(total_padron * participacion)
            votos_validos_estimados = int(votantes_estimados * votos_validos_pct)
            
            st.metric("Padrón Total PBA", f"{total_padron:,}")
            st.metric("Votantes Estimados", f"{votantes_estimados:,}")
            st.metric("Votos Válidos Estimados", f"{votos_validos_estimados:,}")
            
            # Bancas totales
            total_bancas_dip = sum(data['secciones_diputados'].values())
            total_bancas_sen = sum(data['secciones_senadores'].values())
            
            st.metric("Bancas en Juego - Diputados", total_bancas_dip)
            st.metric("Bancas en Juego - Senadores", total_bancas_sen)

# Información adicional en la sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Información")
st.sidebar.info("""
Esta aplicación simula las elecciones legislativas de la Provincia de Buenos Aires 2025 
utilizando el sistema D'Hondt y simulaciones Monte Carlo con distribuciones Dirichlet.

**Características:**
- Simulación probabilística de resultados
- Sistema D'Hondt oficial de Argentina
- Datos reales de padrón electoral
- Visualizaciones interactivas
""")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>🗳️ Simulador Electoral PBA 2025 | Desarrollado con Streamlit</p>
</div>
""", unsafe_allow_html=True) 