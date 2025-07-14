# 🗳️ Simulador Electoral PBA 2025

Una aplicación web interactiva para simular las elecciones legislativas de la Provincia de Buenos Aires 2025, utilizando el sistema D'Hondt y simulaciones Monte Carlo.

## 🚀 Características

- **Simulación Probabilística**: Utiliza distribuciones Dirichlet para modelar la incertidumbre electoral
- **Sistema D'Hondt**: Implementa el sistema electoral oficial de Argentina
- **Datos Reales**: Basado en padrón electoral actualizado y estructura legislativa actual
- **Visualizaciones Interactivas**: Gráficos de distribución, diagramas de parlamento y tablas resumen
- **Configuración Flexible**: Ajusta participación, intención de voto y parámetros de simulación

## 📋 Requisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## 🛠️ Instalación

1. **Clona o descarga este repositorio**

2. **Instala las dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

## 🎯 Uso

1. **Ejecuta la aplicación**:
   ```bash
   streamlit run app.py
   ```

2. **Abre tu navegador** en la dirección que aparece (generalmente `http://localhost:8501`)

3. **Configura los parámetros** en la barra lateral:
   - Participación electoral
   - Porcentaje de votos válidos  
   - Intención de voto por partido
   - Número de simulaciones Monte Carlo

4. **Haz clic en "🚀 Ejecutar Simulación"** para generar los resultados

## 📊 Funcionalidades

### Parámetros Configurables

- **Participación Electoral**: Porcentaje del padrón que vota (40-85%)
- **Votos Válidos**: Porcentaje de votos no nulos (80-98%)
- **Intención de Voto**: Distribución porcentual entre los 5 principales espacios políticos
- **Simulaciones Monte Carlo**: Número de corridas (100-2000)
- **Parámetros Técnicos**: Escala Alpha y Phi Jerárquico para el modelo Dirichlet

### Resultados Generados

1. **Resumen Ejecutivo**: Medidas de tendencia central y intervalos de confianza
2. **Distribuciones de Probabilidad**: Gráficos KDE de las simulaciones
3. **Diagramas de Parlamento**: Visualización semicircular de la composición legislativa
4. **Detalles Técnicos**: Parámetros utilizados y estadísticas del modelo

## 🏛️ Cámaras Simuladas

### Cámara de Diputados
- **Secciones que votan**: Capital, Segunda, Tercera, Sexta
- **Bancas en juego**: 46 de 92 totales
- **Sistema**: D'Hondt con umbral implícito

### Senado Provincial  
- **Secciones que votan**: Primera, Cuarta, Quinta, Séptima
- **Bancas en juego**: 23 de 46 totales
- **Sistema**: D'Hondt con umbral implícito

## 🎲 Metodología

### Modelo Electoral

1. **Base Probabilística**: Cada simulación genera proporción de votos usando distribución Dirichlet
2. **Conversión a Votos**: Aplica participación y validez para calcular votos absolutos
3. **Reparto de Bancas**: Usa algoritmo D'Hondt oficial (con manejo del Art. 110)
4. **Agregación**: Suma bancas no renovadas de elecciones anteriores

### Espacios Políticos

- **Alianza La Libertad Avanza**: PRO + LLA
- **Fuerza Patria**: Unión por la Patria  
- **Somos Buenos Aires**: UCR + PJ no kirchnerista
- **Avanza Libertad**: Libertarios disidentes
- **FIT-U**: Frente de Izquierda

## 📈 Interpretación de Resultados

- **Media**: Valor esperado de bancas por partido
- **P5/P95**: Intervalo de confianza del 90%
- **Medoid**: Resultado más representativo (mínima distancia a todas las simulaciones)
- **Densidad**: Probabilidad relativa de cada cantidad de bancas

## ⚠️ Limitaciones

- No considera efectos de campaña o eventos no previstos
- Asume distribución homogénea dentro de cada sección
- Parámetros basados en tendencias históricas y encuestas disponibles
- No incluye listas locales o candidaturas testimoniales

## 🔧 Desarrollo

### Estructura del Código

```
app.py              # Aplicación principal Streamlit
requirements.txt    # Dependencias Python
README.md          # Documentación
analisis/
  └── calculo.ipynb # Notebook original con análisis exploratorio
```

### Librerías Principales

- **streamlit**: Interface web interactiva
- **pandas/numpy**: Manipulación de datos y cálculos
- **scipy**: Distribuciones estadísticas
- **geopandas**: Manejo de datos geoespaciales  
- **matplotlib/plotly**: Visualizaciones
- **poli-sci-kit**: Diagramas de parlamento

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia MIT.

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📞 Contacto

Para preguntas, sugerencias o reportes de bugs, por favor abre un issue en el repositorio.

---

*Desarrollado con usando Python y Streamlit* 