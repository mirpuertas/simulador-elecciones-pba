import pandas as pd

def repartir_bancas(df: pd.DataFrame) -> pd.DataFrame:
    out = []

    for seccion, grupo in df.groupby("seccion"):
        total_votos = grupo["votos"].sum()
        cargos      = grupo["cargos"].iloc[0]
        cuociente   = max(1, total_votos // cargos)        # Asegura >= 1

        grupo = grupo.copy()
        grupo["enteros"] = grupo["votos"] // cuociente
        grupo["residuo"] = grupo["votos"] %  cuociente
        grupo["bancas"]  = grupo["enteros"]

        # Restos solo entre listas con >= 1 cuociente
        faltan = cargos - grupo["bancas"].sum()
        
        if faltan > 0:  # Solo asignar si realmente faltan bancas
            elig = grupo[grupo["enteros"] > 0]
            if not elig.empty:
                idx = (elig.sort_values(["residuo", "votos"],
                                        ascending=False)
                             .head(faltan).index)
                grupo.loc[idx, "bancas"] += 1

        # ── Art. 110: nadie alcanzó cuociente
        if grupo["bancas"].sum() == 0:
            q = cuociente
            while grupo["bancas"].sum() == 0:
                q = max(1, q // 2)
                grupo["enteros"] = grupo["votos"] // q
                grupo["residuo"] = grupo["votos"] %  q
                grupo["bancas"]  = grupo["enteros"]

                faltan = cargos - grupo["bancas"].sum()
                
                if faltan > 0:  # Solo asignar si realmente faltan bancas
                    elig = grupo[grupo["enteros"] > 0]
                    if not elig.empty:
                        idx = (elig.sort_values(["residuo", "votos"],
                                                ascending=False)
                                       .head(faltan).index)
                        grupo.loc[idx, "bancas"] += 1
                elif faltan < 0:
                    elig = grupo[grupo["bancas"] > 0]
                    if not elig.empty:
                        idx = (elig.sort_values(["residuo", "votos"],
                                                ascending=True)
                                       .head(-faltan).index)
                        grupo.loc[idx, "bancas"] -= 1

        # Completar con la lista más votada
        faltan = cargos - grupo["bancas"].sum()
        if faltan:
            top = grupo["votos"].idxmax()
            grupo.loc[top, "bancas"] += faltan

        out.append(grupo[["seccion", "lista", "bancas"]])

    # Concatenar resultados y ordenar
    return (
        pd.concat(out, ignore_index=True)        
          .sort_values(["seccion", "lista"])      
          .reset_index(drop=True)                
    )
