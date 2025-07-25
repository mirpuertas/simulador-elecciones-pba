import geopandas as gpd
from shapely.geometry import Point

def obtener_centroides_seguros(gdf: gpd.GeoDataFrame, epsg_proj: int = 3857) -> gpd.GeoSeries:
    """
    Calcula centroides geométricamente correctos para un GeoDataFrame con CRS geográfico.
    
    Parameters:
        gdf: GeoDataFrame original (puede estar en EPSG:4326 u otro)
        epsg_proj: CRS proyectado para cálculo geométrico (por defecto Web Mercator)
    
    Returns:
        GeoSeries de centroides reproyectados al CRS original del gdf
    """
    crs_original = gdf.crs
    gdf_proj = gdf.to_crs(epsg=epsg_proj)
    centroides_proj = gdf_proj.geometry.centroid
    centroides_final = centroides_proj.to_crs(crs_original)
    return centroides_final
