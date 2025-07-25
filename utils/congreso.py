import json
import pandas as pd
from collections import defaultdict

def nested_defaultdict_int():
    return defaultdict(int)

class Congreso:
    def __init__(self, json_path, csv_path):
        self.estructura = self._cargar_json(json_path)
        self.df_composicion = pd.read_csv(csv_path)
        self.partido_a_alianza = self._crear_mapeo_partido_alianza()
        self.composicion_actual = self._calcular_composicion(solo_no_renueva=False)
        self.bancas_no_disputadas = self._calcular_composicion(solo_no_renueva=True)

    def _cargar_json(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _crear_mapeo_partido_alianza(self):
        mapeo = {}
        for alianza, datos in self.estructura["alianzas"].items():
            for partido in datos["partidos"]:
                mapeo[partido.strip().upper()] = alianza
        return mapeo

    def _normalizar_partido(self, nombre):
        return nombre.strip().upper()

    def _calcular_composicion(self, solo_no_renueva=False):
        resultado = {
            "diputados": defaultdict(nested_defaultdict_int),
            "senadores": defaultdict(nested_defaultdict_int)
        }

        for _, row in self.df_composicion.iterrows():
            if solo_no_renueva and row["renueva"].strip().upper() != "NO":
                continue

            camara = row["camara"].strip().lower()
            seccion = row["seccion"].strip()
            partido = self._normalizar_partido(row["partido_politico"])
            camara_clave = "diputados" if camara == "diputados" else "senadores"
            alianza = self.partido_a_alianza.get(partido, partido)
            resultado[camara_clave][seccion][alianza] += 1

        return resultado
       
    def obtener_secciones_por_alianza(self) -> dict[str, set[str]]:
        resultado = {}
        padron_keys = set(self.estructura["padron"].keys())

        for alianza, datos in self.estructura["alianzas"].items():
            raw = datos.get("secciones", "Todas")

            if raw is None:
                continue

            if raw is None or str(raw).strip().lower() == "todas":
                resultado[alianza] = padron_keys
            else:
                resultado[alianza] = set(map(str.strip, str(raw).split(",")))

        return resultado

    def obtener_bancas_por_seccion(self):
        return self.estructura["bancas_por_seccion"]

    def obtener_padron(self):
        return self.estructura["padron"]
    
    def obtener_colores_alianzas(self):
        return {a: v["color"] for a, v in self.estructura["alianzas"].items()}

    def obtener_composicion_actual(self):
        return self.composicion_actual

    def obtener_bancas_no_disputadas(self):
        return self.bancas_no_disputadas

    def obtener_alianza_de(self, partido):
        return self.partido_a_alianza.get(self._normalizar_partido(partido), None)
