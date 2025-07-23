from pathlib import Path
from utils.congreso import Congreso
import configparser


def cargar_congreso(anio: int | None = None) -> Congreso:
    """Devuelve una instancia de `Congreso` para el año solicitado.

    Si `anio` es None, intenta leerlo de un archivo `config.ini` ubicado en la
    raíz del proyecto con la clave `año_vigente` en la sección `[simulador]`.
    """
    base_dir = Path(__file__).resolve().parents[1]  # /path/to/simulador_pba

    # Si no se pasa explícitamente el año, carga desde config.ini
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

    # Construye rutas de archivos de datos
    data_dir = base_dir / "data"
    json_path = data_dir / f"estructura_congreso_completa_{anio}.json"
    csv_path = data_dir / f"congreso_composicion_inicial_{anio}.csv"

    if not json_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo {json_path}")
    if not csv_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo {csv_path}")

    return Congreso(json_path, csv_path)
