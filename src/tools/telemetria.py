"""
Tool determinista sobre datos de telemetría de nodos IoT de Auvix
(Datos_Nodos_Julio_2026.xlsx).

Esquema (30 registros, 1 lectura diaria por nodo, julio 2026, sin nulos):
    Fecha                   -> str 'YYYY-MM-DD' (se convierte a datetime
                                internamente, nunca se expone así al LLM)
    Node_ID                 -> str, 3 valores: NODO-L4-01/02/03
    Temperatura_Promedio_C  -> float
    Consumo_kWh             -> float
    Latencia_ms             -> float
    Estado_Nodo             -> str, 'Operativo' o 'Alerta'
"""
from __future__ import annotations
import unicodedata
import pandas as pd
from src.ingestion.loaders import load_tabular

RUTA_XLSX_POR_DEFECTO = "data/raw/Datos_Nodos_Julio_2026.xlsx"
METRICAS_VALIDAS = {
    "temperatura": "Temperatura_Promedio_C",
    "consumo": "Consumo_kWh",
    "latencia": "Latencia_ms",
}

# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """Normaliza texto para comparaciones insensibles a mayúsculas/acentos."""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def cargar_datos_telemetria(filepath: str = RUTA_XLSX_POR_DEFECTO) -> pd.DataFrame:
    """
    Carga el XLSX de telemetría como DataFrame, con 'Fecha' ya convertida
    a datetime (aquí sí la necesitamos como fecha real para ordenar historial y detectar
    la lectura más reciente).
    """
    df = load_tabular(filepath)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    return df


def _lectura_a_dict(fila: pd.Series) -> dict:
    """Convierte una fila de telemetría en un dict compacto para el LLM."""
    return {
        "fecha": fila["Fecha"].strftime("%Y-%m-%d"),
        "node_id": fila["Node_ID"],
        "temperatura_c": round(float(fila["Temperatura_Promedio_C"]), 2),
        "consumo_kwh": round(float(fila["Consumo_kWh"]), 2),
        "latencia_ms": round(float(fila["Latencia_ms"]), 2),
        "estado_nodo": fila["Estado_Nodo"],
    }

def _nodos_validos(df: pd.DataFrame) -> list[str]:
    return sorted(df["Node_ID"].unique().tolist())

# ---------------------------------------------------------------------------
# 1. Histórico y estado actual por nodo
# ---------------------------------------------------------------------------

def historico_por_nodo(df: pd.DataFrame, node_id: str) -> dict:
    """
    Devuelve el estado más reciente de un nodo + su historial completo
    de lecturas, ordenado cronológicamente.

    Pregunta que resuelve: "¿Cómo está el NODO-L4-03?" /
    "¿Cuál es el historial del nodo X?"
    """
    mask = df["Node_ID"].apply(_normalizar) == _normalizar(node_id)
    subset = df[mask].sort_values("Fecha")

    if subset.empty:
        return {
            "encontrado": False,
            "node_id_consultado": node_id,
            "mensaje": f"No existe el nodo '{node_id}' en los datos.",
            "nodos_disponibles": _nodos_validos(df),
        }

    ultima_lectura = subset.iloc[-1]

    return {
        "encontrado": True,
        "node_id": ultima_lectura["Node_ID"],
        "cantidad_lecturas": int(len(subset)),
        "estado_actual": ultima_lectura["Estado_Nodo"],
        "fecha_ultima_lectura": ultima_lectura["Fecha"].strftime("%Y-%m-%d"),
        "historial": [_lectura_a_dict(fila) for _, fila in subset.iterrows()],
    }


# ---------------------------------------------------------------------------
# 2. Nodos en alerta
# ---------------------------------------------------------------------------

def nodos_en_alerta(df: pd.DataFrame) -> dict:
    """
    Lista todas las lecturas en estado 'Alerta', agrupando también
    qué nodos se vieron afectados al menos una vez.

    Pregunta que resuelve: "¿Qué nodos tienen o tuvieron alertas?"
    """
    subset = df[df["Estado_Nodo"].apply(_normalizar) == _normalizar("Alerta")]
    subset = subset.sort_values("Fecha")

    if subset.empty:
        return {
            "hay_alertas": False,
            "mensaje": "No se registran lecturas en estado 'Alerta'.",
        }

    return {
        "hay_alertas": True,
        "cantidad_lecturas_en_alerta": int(len(subset)),
        "nodos_afectados": sorted(subset["Node_ID"].unique().tolist()),
        "lecturas_en_alerta": [_lectura_a_dict(fila) for _, fila in subset.iterrows()],
    }


# ---------------------------------------------------------------------------
# 3. Promedios por nodo
# ---------------------------------------------------------------------------

def promedio_por_nodo(df: pd.DataFrame, node_id: str) -> dict:
    """
    Calcula promedios de temperatura, consumo y latencia para un nodo
    específico, sobre todas sus lecturas.

    Pregunta que resuelve: "¿Cuál es la temperatura/consumo/latencia
    promedio del nodo X?"
    """
    mask = df["Node_ID"].apply(_normalizar) == _normalizar(node_id)
    subset = df[mask]

    if subset.empty:
        return {
            "encontrado": False,
            "node_id_consultado": node_id,
            "mensaje": f"No existe el nodo '{node_id}' en los datos.",
            "nodos_disponibles": _nodos_validos(df),
        }

    return {
        "encontrado": True,
        "node_id": subset["Node_ID"].iloc[0],
        "cantidad_lecturas": int(len(subset)),
        "temperatura_promedio_c": round(float(subset["Temperatura_Promedio_C"].mean()), 2),
        "consumo_promedio_kwh": round(float(subset["Consumo_kWh"].mean()), 2),
        "latencia_promedio_ms": round(float(subset["Latencia_ms"].mean()), 2),
    }


# ---------------------------------------------------------------------------
# 4. Resumen general
# ---------------------------------------------------------------------------

def resumen_general(df: pd.DataFrame) -> dict:
    """
    Resumen agregado por nodo (promedios + cantidad de alertas) más un
    total global, para preguntas abiertas tipo "¿cómo está la red de
    nodos IoT?".
    """
    agregado = (
        df.groupby("Node_ID")
        .agg(
            cantidad_lecturas=("Node_ID", "count"),
            temperatura_promedio_c=("Temperatura_Promedio_C", "mean"),
            consumo_promedio_kwh=("Consumo_kWh", "mean"),
            latencia_promedio_ms=("Latencia_ms", "mean"),
        )
        .round(2)
        .reset_index()
    )

    alertas_por_nodo = (
        df[df["Estado_Nodo"] == "Alerta"]["Node_ID"].value_counts().to_dict()
    )

    por_nodo = [
        {
            "node_id": fila["Node_ID"],
            "cantidad_lecturas": int(fila["cantidad_lecturas"]),
            "temperatura_promedio_c": float(fila["temperatura_promedio_c"]),
            "consumo_promedio_kwh": float(fila["consumo_promedio_kwh"]),
            "latencia_promedio_ms": float(fila["latencia_promedio_ms"]),
            "cantidad_alertas": int(alertas_por_nodo.get(fila["Node_ID"], 0)),
        }
        for _, fila in agregado.iterrows()
    ]

    return {
        "cantidad_nodos": int(df["Node_ID"].nunique()),
        "cantidad_lecturas_global": int(len(df)),
        "cantidad_alertas_global": int((df["Estado_Nodo"] == "Alerta").sum()),
        "por_nodo": por_nodo,
    }


# ---------------------------------------------------------------------------
# 5. Lectura más alta / más baja por métrica
# ---------------------------------------------------------------------------

def _validar_metrica(metrica: str) -> str | dict:
    """
    Traduce el alias en español (ej. 'temperatura') a la columna real
    del DataFrame. Devuelve un dict de error si el alias no existe,
    para que el LLM pueda avisar en lugar de fallar con una excepción.
    """
    alias = _normalizar(metrica)
    if alias not in METRICAS_VALIDAS:
        return {
            "encontrado": False,
            "metrica_consultada": metrica,
            "mensaje": f"Métrica '{metrica}' no reconocida.",
            "metricas_disponibles": list(METRICAS_VALIDAS.keys()),
        }
    return METRICAS_VALIDAS[alias]


def lectura_mas_alta(df: pd.DataFrame, metrica: str) -> dict:
    """
    Pregunta que resuelve: "¿Cuál fue la lectura más alta de
    temperatura/consumo/latencia, y en qué nodo?"
    """
    columna = _validar_metrica(metrica)
    if isinstance(columna, dict):
        return columna

    fila = df.loc[df[columna].idxmax()]
    return {"tipo": "mas_alta", "metrica": metrica, "lectura": _lectura_a_dict(fila)}


def lectura_mas_baja(df: pd.DataFrame, metrica: str) -> dict:
    """
    Pregunta que resuelve: "¿Cuál fue la lectura más baja de
    temperatura/consumo/latencia, y en qué nodo?"
    """
    columna = _validar_metrica(metrica)
    if isinstance(columna, dict):
        return columna

    fila = df.loc[df[columna].idxmin()]
    return {"tipo": "mas_baja", "metrica": metrica, "lectura": _lectura_a_dict(fila)}


# ---------------------------------------------------------------------------
# Prueba manual rápida
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    df = cargar_datos_telemetria()

    print("=== historico_por_nodo('NODO-L4-03') ===")
    print(json.dumps(historico_por_nodo(df, "NODO-L4-03"), indent=2, ensure_ascii=False)[:800], "...")

    print("\n=== nodos_en_alerta() ===")
    print(json.dumps(nodos_en_alerta(df), indent=2, ensure_ascii=False))

    print("\n=== promedio_por_nodo('nodo-l4-01') (minúsculas, prueba normalización) ===")
    print(json.dumps(promedio_por_nodo(df, "nodo-l4-01"), indent=2, ensure_ascii=False))

    print("\n=== resumen_general() ===")
    print(json.dumps(resumen_general(df), indent=2, ensure_ascii=False))

    print("\n=== lectura_mas_alta('temperatura') ===")
    print(json.dumps(lectura_mas_alta(df, "temperatura"), indent=2, ensure_ascii=False))

    print("\n=== lectura_mas_baja('latencia') ===")
    print(json.dumps(lectura_mas_baja(df, "latencia"), indent=2, ensure_ascii=False))

    print("\n=== nodo inexistente (prueba de manejo de error) ===")
    print(json.dumps(historico_por_nodo(df, "NODO-L4-99"), indent=2, ensure_ascii=False))

    print("\n=== métrica inexistente (prueba de manejo de error) ===")
    print(json.dumps(lectura_mas_alta(df, "presion"), indent=2, ensure_ascii=False))