from pathlib import Path
import geopandas as gpd

import configparser
from functools import cache

from utils.congreso import Congreso


@cache
def cargar_congreso(anio: int | None = None) -> Congreso:
    """
    Devuelve una instancia de :class:`utils.congreso.Congreso` para el
    año solicitado.

    Si ``anio`` es ``None`` el valor se toma de ``config.ini`` (sección
    ``[simulador]``, clave ``año_vigente``).

    Parameters
    ----------
    anio : int | None, default ``None``
        Año para el que se desea cargar la estructura del Congreso.
        Cuando es ``None`` se busca la clave indicada en el archivo de
        configuración del proyecto.

    Returns
    -------
    utils.congreso.Congreso
        Objeto inicializado con los datos ``JSON`` y ``CSV`` del año
        correspondiente.

    Raises
    ------
    FileNotFoundError
        Si no existe ``config.ini`` (cuando ``anio`` es ``None``) o si
        los archivos de datos requeridos no se encuentran.
    ValueError
        Cuando la clave ``año_vigente`` falta o no es un entero válido
        dentro de ``config.ini``.
    """
    base_dir = Path(__file__).resolve().parents[1]

    if anio is None:
        config_path = base_dir / "config.ini"
        if not config_path.exists():
            raise FileNotFoundError(
                "No se encuentra config.ini y no se proporcionó año explícito."
            )
        cfg = configparser.ConfigParser()
        cfg.read(config_path, encoding="utf-8")
        try:
            anio = int(cfg["simulador"]["año_vigente"])
        except (KeyError, ValueError):
            raise ValueError(
                "El archivo config.ini debe tener [simulador] y la clave 'año_vigente'."
            )

    data_dir = base_dir / "data"
    json_path = data_dir / f"estructura_congreso_completa_{anio}.json"
    csv_path = data_dir / f"congreso_composicion_inicial_{anio}.csv"

    if not json_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo {json_path}")
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo {csv_path}")

    return Congreso(json_path, csv_path)

def leer_epsg_proyectado(default: int = 22185) -> int:
    """
    Lee el código EPSG a utilizar para proyectar geometrías.

    Parameters
    ----------
    default : int, default ``22185``
        EPSG que se devolverá si la clave no existe en ``config.ini``.

    Returns
    -------
    int
        Código EPSG (entero) configurado en ``config.ini`` o el valor
        por defecto suministrado.
    """
    cfg = configparser.ConfigParser()
    base = Path(__file__).resolve().parents[1]
    cfg.read(base / "config.ini", encoding="utf-8")
    return int(cfg["simulador"].get("epsg_proj", default))

@cache
def cargar_secciones_geojson(path: str | None = None) -> gpd.GeoDataFrame:
    """
    Carga (y cachea) el *GeoJSON* con los polígonos de secciones electorales.

    Parameters
    ----------
    path : str | None, default ``None``
        Ruta al archivo GeoJSON.  Si es ``None`` se usa
        ``data/secciones-electorales-pba.geojson`` relativa al proyecto.

    Returns
    -------
    geopandas.GeoDataFrame
        GeoDataFrame con las geometrías de cada sección.
    """
    if path is None:
        base = Path(__file__).resolve().parents[1]
        path = base / "data" / "secciones-electorales-pba.geojson"

    gdf = gpd.read_file(path)
    return gdf
