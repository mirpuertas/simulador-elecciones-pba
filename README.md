# 🗳️ Simulador Electoral PBA 2025

Aplicación [Streamlit](https://simulador-elecciones-pba.streamlit.app) para estimar la distribución de bancas de la Provincia de Buenos Aires según el **cociente Hare + residuos** (art. 109 y art. 110 de la Constitución provincial).  Permite trabajar en dos niveles:

- **Modo Básico (determinista)** – reparte bancas exactamente a partir de los porcentajes que ingreses.
- **Modo Avanzado (β – Monte Carlo)** – genera miles de sorteos Dirichlet para medir incertidumbre (EN DESARROLLO).

Las secciones electorales, alianzas y padrones provienen de los archivos del año vigente.  Bastan **dos archivos JSON/CSV** para cargar otro año (2027, 2029…).

Las secciones electorales, alianzas y padrones provienen de los archivos del año vigente.  Bastan dos archivos JSON/CSV para cargar otro año (2027, 2029…).

## Funcionalidades

| Característica                    | Detalle                                                                               |
| --------------------------------- | ------------------------------------------------------------------------------------- |
| **Asignación de bancas**          | Cociente Hare + reparto por residuos, validado contra resultados oficiales 2021‑2023. |
| **Intención de voto por sección** | Sliders globales y, opcionalmente, sliders por sección.                               |
| **Mapas interactivos**            | Bancas ganadas, diferencias y partido ganador por sección.                            |
| **Parlamento semicircular**       | Visualización con *poli‑sci‑kit*.                                                     |
| **Arquitectura modular**          | Backend puro (sin Streamlit) + frontend UI; listo para API o CLI.                     |


## Estructura del proyecto

```
├── app.py                 # Punto de entrada: construye contexto y llama a UI
├── config.ini             # Año vigente y configuración global
├── data/
│   ├─ estructura_congreso_completa_2025.json
│   ├─ congreso_composicion_inicial_2025.csv
│   └─ secciones_pba.geojson
└── utils/
    ├─ calculos.py         # Reglas deterministas (diputados‑senadores)
    ├─ cuociente.py        # Algoritmo Hare + residuos
    ├─ ui.py               # Interfaz y visualización en Streamlit
    ├─ plots.py            # Mapas, parlamento
    ├─ geotools.py         # Centroides seguros (EPSG 22185)
    ├─ congreso.py         # DTO + validación de JSON/CSV
    └─ loader.py           # Carga de estructura y caché
```

## Instalación rápida

```bash
# Clonar el repo y entrar
git clone https://github.com/mirpuertas/simulador-elecciones-pba.git
cd simulador-elecciones-pba

# Crear entorno (recomendado: conda o mamba) y activar
mamba env create -f environment.yml           # o conda env create ...
conda activate simulador-elecciones-pba

# Lanzar la aplicación
streamlit run app.py
```
También podés instalarlo con pip si no usás Conda:
```
pip install -r requirements.txt
streamlit run app.py
```

> **Nota:**  `geopandas` requiere GEOS/PROJ.  En Windows usá `mambaforge`; en Linux podés instalar las libs del sistema (`libgeos-dev`, `proj-bin`, `gdal`).

## Uso de la interfaz

1. **Elegí las alianzas visibles** (se sugiere un set mínimo).
2. Ajustá **participación** y **% de votos válidos**.
3. Definí la **intención de voto global** (sliders).
4. (Opcional) Activá *configuración por sección* y personalizá sliders locales.
5. Clic en **🚀 Ejecutar cálculo**.
6. Explorá tabs: **Bancas ganadas · Parlamento · Detalles**.

## Datos de entrada

| Archivo                                   | Propósito                                  |
| ----------------------------------------- | ------------------------------------------ |
| `estructura_congreso_completa_<año>.json` | Padrones, bancas por sección, alianzas.    |
| `congreso_composicion_inicial_<año>.csv`  | Banca vigente (para calcular diferencias). |
| `secciones-electorales-pba.geojson`       | Geometría de las 8 secciones electorales.  |

Cambiar de año = añadir el par JSON/CSV con el mismo esquema y ajustar `año_vigente`.

## Conceptos clave

- **Cociente Hare** ⇒ `total_votos / cargos`; cada lista recibe ⌊ votos / cuociente ⌋ bancas.  Restantes se asignan por mayor residuo.

## Licencia

Este proyecto está bajo la licencia MIT. [Ver LICENSE.](https://github.com/mirpuertas/simulador-elecciones-pba/blob/main/LICENSE)

## Autor

Miguel Ignacio Rodríguez Puertas — [@mirpuertas](https://github.com/mirpuertas)
