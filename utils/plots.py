import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import poli_sci_kit.plot as pk

import numpy as np
from scipy.stats import gaussian_kde

from typing import Mapping



def crear_mapa_bancas_ganadas(gdf_secciones, bancas_ganadas_df, alianza, titulo, ax=None):
    """Crea un mapa estático de bancas ganadas por alianza."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.get_figure()
    
    # Preparar datos
    gdf_plot = gdf_secciones.copy()
    gdf_plot["bancas"] = gdf_plot["seccion"].map(bancas_ganadas_df[alianza]).fillna(0)
    
    # Definir colores
    vmax = gdf_plot["bancas"].max()
    if vmax == 0:
        ax.text(0.5, 0.5, "No hay bancas ganadas para mostrar", transform=ax.transAxes, 
                ha='center', va='center', fontsize=12)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(titulo)
        return fig
    
    # Crear mapa con escala de colores desde 0 (blanco/gris claro) hasta vmax
    gdf_plot.plot(
        column="bancas",
        cmap="Blues",
        vmin=0,
        vmax=vmax,
        ax=ax,
        legend=True,
        legend_kwds={'label': 'Bancas ganadas', 'shrink': 0.8},
        edgecolor='black',
        linewidth=0.5
    )
    
    # Agregar anotaciones con números de bancas
    for idx, row in gdf_plot.iterrows():
        if row["bancas"] > 0:
            centroid = row.geometry.centroid
            ax.annotate(
                f'{int(row["bancas"])}',
                (centroid.x, centroid.y),
                ha='center', va='center',
                fontsize=9, fontweight='bold',
                color='white',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='navy', alpha=0.8)
            )
    
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_axis_off()
    return fig


def crear_mapa_diferencias_estatico(gdf_secciones, cambios_df, alianza, titulo, ax=None):
    """Crea un mapa estático de diferencias de bancas por alianza."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.get_figure()
    
    # Preparar datos
    gdf_plot = gdf_secciones.copy()
    gdf_plot["ganancia"] = gdf_plot["seccion"].map(cambios_df[alianza]).fillna(0)
    
    # Definir colores
    vmax = gdf_plot["ganancia"].abs().max()
    if vmax == 0:
        ax.text(0.5, 0.5, "No hay cambios para mostrar", transform=ax.transAxes, 
                ha='center', va='center', fontsize=12)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(titulo)
        return fig
    
    # Crear mapa
    gdf_plot.plot(
        column="ganancia",
        cmap="RdYlGn",
        vmin=-vmax,
        vmax=vmax,
        ax=ax,
        legend=True,
        legend_kwds={'label': 'Ganancia de bancas', 'shrink': 0.8}
    )
    
    # Agregar anotaciones con números
    for idx, row in gdf_plot.iterrows():
        if abs(row["ganancia"]) > 0:
            centroid = row.geometry.centroid
            ax.annotate(
                f'{int(row["ganancia"]):+d}',
                (centroid.x, centroid.y),
                ha='center', va='center',
                fontsize=8, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8)
            )
    
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_axis_off()
    return fig


def crear_mapa_ganadores(gdf_secciones, bancas_totales_df, colores_partidos, titulo, ax=None):
    """Crea un mapa mostrando el partido ganador por sección."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.get_figure()
    
    # Calcular ganador por sección
    ganadores = bancas_totales_df.idxmax(axis=1)
    max_bancas = bancas_totales_df.max(axis=1)
    
    # Preparar datos
    gdf_plot = gdf_secciones.copy()
    gdf_plot["ganador"] = gdf_plot["seccion"].map(ganadores).fillna("Sin datos")
    gdf_plot["max_bancas"] = gdf_plot["seccion"].map(max_bancas).fillna(0)
    
    # Crear mapa base con bordes para todas las secciones
    gdf_plot.plot(
        color="#F0F0F0",  # Color gris claro para secciones sin datos
        ax=ax,
        edgecolor='black',
        linewidth=0.5
    )
    
    # Superponer colores de ganadores
    for ganador in gdf_plot["ganador"].unique():
        if ganador != "Sin datos":
            subset = gdf_plot[gdf_plot["ganador"] == ganador]
            subset.plot(
                color=colores_partidos.get(ganador, "#CCCCCC"),
                ax=ax,
                label=ganador,
                edgecolor='black',
                linewidth=0.5
            )
    
    # Agregar anotaciones con números de bancas
    for idx, row in gdf_plot.iterrows():
        if row["max_bancas"] > 0:
            centroid = row.geometry.centroid
            ax.annotate(
                f'{int(row["max_bancas"])}',
                (centroid.x, centroid.y),
                ha='center', va='center',
                fontsize=9, fontweight='bold',
                color='white',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='black', alpha=0.7)
            )
    
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_axis_off()
    
    # Construir leyenda manualmente
    legend_elements = []
    for ganador in gdf_plot["ganador"].unique():
        if ganador != "Sin datos":
            color = colores_partidos.get(ganador, "#CCCCCC")
            legend_elements.append(Patch(facecolor=color, edgecolor='black', label=ganador))

    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1, 1))
    
    return fig

def plot_distribucion(df, colores: Mapping[str, str], ax=None):
    if df is None or df.empty:
        raise ValueError("DataFrame vacío")
    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))
    for alianza, datos in df.items():      # df.columns → series
        xs = np.linspace(datos.min(), datos.max(), 400)
        dens = gaussian_kde(datos)(xs)
        ax.plot(xs, dens, label=alianza,
                color=colores.get(alianza, "#888"))
    ax.legend(); ax.grid(True, alpha=0.3)
    return ax.get_figure()

def crear_parlamento(series, titulo, colores: Mapping[str, str]):
    series = series[series > 0].sort_values(ascending=False)
    if series.empty:
        return None
    fig, ax = plt.subplots(figsize=(8, 4.5))
    pk.parliament(
        allocations=series.tolist(),
        labels=series.index.tolist(),
        colors=[colores.get(a, "#999") for a in series.index],
        style="semicircle", num_rows=5 if "Diput" in titulo else 3,
        marker_size=180, legend=True, axis=ax,
    )
    ax.set_title(titulo, fontsize=16, weight="bold")

    total_bancas = series.sum()
    ax.text(0, 0, str(total_bancas), ha='center', va='center',
            fontsize=20, fontweight='bold', color='gray', alpha=0.6)
    
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.1),
              ncol=3, frameon=False)
    
    return fig

