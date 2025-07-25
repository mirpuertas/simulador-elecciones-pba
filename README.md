# 🗳️ Simulador Electoral PBA 2025

App interactiva para simular elecciones legislativas en la Provincia de Buenos Aires, utilizando el sistema de cociente Hare con distribución por residuos. Permite definir intención de voto por sección electoral, ejecutar simulaciones y visualizar los resultados de forma clara e interactiva.

## Funcionalidades

- **Asignación de bancas** por cociente electoral (Hare) + residuos
- Modo **determinista** (asignación exacta) y **Monte Carlo** (simulación aleatoria)
- Definición de intención de voto por sección electoral
- Mapa interactivo con actualización por sección
- Modo avanzado: edición detallada por sección (sliders)
- Visualización de resultados en mapas, gráficos y tablas
- Arquitectura **modular y escalable** para otras elecciones (ej. 2027)

## Estructura del proyecto

   ```
├── app.py # Frontend en Streamlit
├── config.ini # Año de elección y parámetros generales
├── data/
│ ├── estructura_congreso_completa_2025.json
│ └── congreso_composicion_inicial_2025.csv
│ └── secciones_pba.geojson # Mapa de secciones electorales
├── utils/
│ ├── congreso.py # Composición actual y mapeo de alianzas
│ ├── loader.py # Carga de archivos por año
│ └── reglas_electorales.py # Reglas de reparto, simulación y resumen
│ └── simulacion.py
│ └── geotools.py
│ └── plots.py
   ```
## Acceder a la versión Online 2025

Simulador

## Cómo ejecutar

### 1. Instalar dependencias

```
pip install -r requirements.txt
```

### 2. Ejecuta la app
```
streamlit run app.py
```

### 3. Interfaz

- Elegí el año electoral
- Seleccioná modo de simulación (determinista / Monte Carlo)
- Definí la intención de voto por sección
- Visualizá mapas, gráficos y resultados parlamentarios

## Datos

- estructura_congreso_completa_<año>.json: define las bancas a renovar y alianzas participantes

- congreso_composicion_inicial_<año>.csv: composición actual del congreso (usado para mostrar cambios)

- secciones_pba.geojson: mapa de secciones electorales

Podés simular nuevos escenarios actualizando los archivos de datos sin modificar el código.

## Conceptos clave

- Cociente electoral Hare: se divide el total de votos válidos por la cantidad de bancas; cada lista obtiene tantas bancas como veces contenga el cociente. Las bancas restantes se reparten según los residuos más altos.
- Simulación Monte Carlo: genera resultados posibles a partir de distribuciones de probabilidad.
- Modo determinista: asigna bancas directamente a partir de los porcentajes ingresados.

## Licencia

Este proyecto está bajo la licencia MIT. [Ver LICENSE.](https://github.com/mirpuertas/simulador-elecciones-pba/blob/main/LICENSE)

## Autor

Miguel Ignacio Rodríguez Puertas · [@mirpuertas](https://github.com/mirpuertas)
