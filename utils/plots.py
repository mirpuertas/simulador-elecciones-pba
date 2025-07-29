from typing import Mapping, Optional
import geopandas as gpd
import pandas as pd
from matplotlib.figure import Figure

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import poli_sci_kit.plot as pk

from utils.geotools import obtener_centroides_seguros

__all__ = ["mapa_bancas_ganadas", "mapa_diferencias_estatico", "mapa_ganadores", "crear_parlamento"]


def mapa_bancas_ganadas(gdf_secciones: gpd.GeoDataFrame,
    bancas_ganadas_df: pd.DataFrame,
    alianza: str,
    titulo: str,
    ax=None,
    epsg_proj: int = 22185
    ) -> Figure:
    """Crea un mapa estático de bancas ganadas por alianza."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.get_figure()
    
    gdf_plot = gdf_secciones.copy()
    gdf_plot["bancas"] = gdf_plot["seccion"].map(bancas_ganadas_df[alianza]).fillna(0)
    
    vmax = gdf_plot["bancas"].max()
    if vmax == 0:
        ax.text(0.5, 0.5, "No hay bancas ganadas para mostrar", transform=ax.transAxes, 
                ha='center', va='center', fontsize=12)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(titulo)
        return fig
    
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

    centroides = obtener_centroides_seguros(gdf_plot, epsg_proj)

    for idx, row in gdf_plot.iterrows():
        if row["bancas"] > 0:
            centroide = centroides.iloc[idx]
            ax.annotate(
                f'{int(row["bancas"])}',
                (centroide.x, centroide.y),
                ha='center', va='center',
                fontsize=9, fontweight='bold',
                color='white',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='navy', alpha=0.8)
            )
    
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_axis_off()
    plt.close(fig)
    return fig


def mapa_diferencias_estatico(gdf_secciones: gpd.GeoDataFrame,
    cambios_df: pd.DataFrame,
    alianza: str,
    titulo: str,
    ax=None,
    epsg_proj: int = 22185
    ) -> Figure:
    """Crea un mapa estático de diferencias de bancas por alianza."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.get_figure()
    
    gdf_plot = gdf_secciones.copy()
    gdf_plot["ganancia"] = gdf_plot["seccion"].map(cambios_df[alianza]).fillna(0)
    
    vmax = gdf_plot["ganancia"].abs().max()
    if vmax == 0:
        ax.text(0.5, 0.5, "No hay cambios para mostrar", transform=ax.transAxes, 
                ha='center', va='center', fontsize=12)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(titulo)
        return fig
    
    gdf_plot.plot(
        column="ganancia",
        cmap="RdYlGn",
        vmin=-vmax,
        vmax=vmax,
        ax=ax,
        legend=True,
        legend_kwds={'label': 'Ganancia de bancas', 'shrink': 0.8}
    )

    centroides = obtener_centroides_seguros(gdf_plot, epsg_proj=epsg_proj)

    for idx, row in gdf_plot.iterrows():
        if abs(row["ganancia"]) > 0:
            centroide = centroides.iloc[idx]
            ax.annotate(
                f'{int(row["ganancia"]):+d}',
                (centroide.x, centroide.y),
                ha='center', va='center',
                fontsize=8, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8)
            )
    
    ax.set_title(titulo, fontsize=14, fontweight='bold')
    ax.set_axis_off()
    plt.close(fig)
    return fig


def mapa_ganadores(gdf_secciones: gpd.GeoDataFrame,
    bancas_totales_df: pd.DataFrame,
    colores_partidos: dict,
    titulo: str,
    ax=None,
    epsg_proj: int = 22185
    ) -> Figure:
    """Crea un mapa mostrando el partido ganador por sección."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.get_figure()
    
    ganadores = bancas_totales_df.idxmax(axis=1)
    max_bancas = bancas_totales_df.max(axis=1)
    
    gdf_plot = gdf_secciones.copy()
    gdf_plot["ganador"] = gdf_plot["seccion"].map(ganadores).fillna("Sin datos")
    gdf_plot["max_bancas"] = gdf_plot["seccion"].map(max_bancas).fillna(0)
    
    gdf_plot.plot(
        color="#F0F0F0", 
        ax=ax,
        edgecolor='black',
        linewidth=0.5
    )
    
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

    centroides = obtener_centroides_seguros(gdf_plot, epsg_proj=epsg_proj)

    for idx, row in gdf_plot.iterrows():
        if row["max_bancas"] > 0:
            centroide = centroides.iloc[idx]
            ax.annotate(
                f'{int(row["max_bancas"])}',
                (centroide.x, centroide.y),
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
    
    plt.close(fig)
    return fig

def crear_parlamento(series, titulo, colores: Mapping[str, str]) -> Optional[Figure]:
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
    
    plt.close(fig)
    return fig

