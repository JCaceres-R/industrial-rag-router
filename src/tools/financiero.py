"""
src/tools/financiero.py

Tool determinista sobre datos financieros de Auvix (DatosFinancieros_Auvix.csv).

Principio de diseño (ver docs/CORPUS.md y ESTADO_PROYECTO.md):
- El LLM decide QUÉ función invocar y con QUÉ parámetros.
- Cada función aquí ejecuta el cálculo real sobre el DataFrame y devuelve
  un diccionario estructurado y compacto — nunca el DataFrame completo,
  nunca una lista larga de filas crudas.

"""

from __future__ import annotations
import unicodedata
from pathlib import Path
import pandas as pd
from src.ingestion.loaders import load_tabular

RUTA_CSV_POR_DEFECTO = "data/raw/DatosFinancieros_Auvix.csv"


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """
    Normaliza texto para comparaciones insensibles a mayúsculas/acentos.
    Ej: 'iot' == 'IoT', 'seguridad ti' == 'Seguridad TI'.
    """
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def cargar_datos_financieros(filepath: str = RUTA_CSV_POR_DEFECTO) -> pd.DataFrame:
    """
    Carga el CSV financiero como DataFrame usando el loader de ingesta.
    Se expone como función separada para poder inyectar un DataFrame.
    """
    return load_tabular(filepath)


def _fila_a_dict(fila: pd.Series) -> dict:
    """Convierte una fila del DataFrame en un dict compacto para el LLM."""
    return {
        "id_transaccion": fila["ID_Transaccion"],
        "fecha": str(fila["Fecha"]),
        "departamento": fila["Departamento"],
        "categoria": fila["Categoria"],
        "descripcion": fila["Descripcion_Articulo"],
        "monto_usd": round(float(fila["Monto_USD"]), 2),
        "estado_aprobacion": fila["Estado_Aprobacion"],
    }


# ---------------------------------------------------------------------------
# 1. Total por departamento
# ---------------------------------------------------------------------------

def total_por_departamento(df: pd.DataFrame, departamento: str) -> dict:
    """
    Suma el gasto total de un departamento, sobre TODAS las transacciones
    (Aprobado + Pendiente + Rechazado), y reporta cuántas hay.
    """
    mask = df["Departamento"].apply(_normalizar) == _normalizar(departamento)
    subset = df[mask]

    if subset.empty:
        departamentos_validos = sorted(df["Departamento"].unique().tolist())
        return {
            "encontrado": False,
            "departamento_consultado": departamento,
            "mensaje": f"No existe el departamento '{departamento}' en los datos.",
            "departamentos_disponibles": departamentos_validos,
        }

    return {
        "encontrado": True,
        "departamento": subset["Departamento"].iloc[0],
        "total_usd": round(float(subset["Monto_USD"].sum()), 2),
        "cantidad_transacciones": int(len(subset)),
        "estado_incluido": "todos",
    }


# ---------------------------------------------------------------------------
# 2. Total por categoría
# ---------------------------------------------------------------------------

def total_por_categoria(df: pd.DataFrame, categoria: str) -> dict:
    """
    Suma el gasto total de una categoría (ej. 'Hardware', 'OpEx'),
    sobre todas las transacciones sin importar su estado de aprobación.
    """
    mask = df["Categoria"].apply(_normalizar) == _normalizar(categoria)
    subset = df[mask]

    if subset.empty:
        categorias_validas = sorted(df["Categoria"].unique().tolist())
        return {
            "encontrado": False,
            "categoria_consultada": categoria,
            "mensaje": f"No existe la categoría '{categoria}' en los datos.",
            "categorias_disponibles": categorias_validas,
        }

    return {
        "encontrado": True,
        "categoria": subset["Categoria"].iloc[0],
        "total_usd": round(float(subset["Monto_USD"].sum()), 2),
        "cantidad_transacciones": int(len(subset)),
        "estado_incluido": "todos",
    }


# ---------------------------------------------------------------------------
# 3. Transacciones por estado
# ---------------------------------------------------------------------------

def transacciones_por_estado(df: pd.DataFrame, estado: str) -> dict:
    """
    Lista las transacciones que se encuentran en un estado de aprobación
    dado (Aprobado / Pendiente / Rechazado).

    Pregunta que resuelve: "¿Qué transacciones están Pendientes/Rechazadas?"

    Nota: si hay muchas coincidencias, se devuelve la lista completa de
    todas formas, porque cada transacción ya es un dict compacto (7 campos
    cortos) — el volumen total sigue siendo mucho menor que enviar el CSV
    completo o el DataFrame crudo.
    """
    mask = df["Estado_Aprobacion"].apply(_normalizar) == _normalizar(estado)
    subset = df[mask]

    if subset.empty:
        estados_validos = sorted(df["Estado_Aprobacion"].unique().tolist())
        return {
            "encontrado": False,
            "estado_consultado": estado,
            "mensaje": f"No existe el estado '{estado}' en los datos.",
            "estados_disponibles": estados_validos,
        }

    return {
        "encontrado": True,
        "estado": subset["Estado_Aprobacion"].iloc[0],
        "cantidad_transacciones": int(len(subset)),
        "total_usd": round(float(subset["Monto_USD"].sum()), 2),
        "transacciones": [_fila_a_dict(fila) for _, fila in subset.iterrows()],
    }


# ---------------------------------------------------------------------------
# 4. Resumen general
# ---------------------------------------------------------------------------

def resumen_general(df: pd.DataFrame) -> dict:
    """
    Resumen agregado por departamento, para preguntas abiertas como
    "¿cómo va el gasto general?" o "dame un resumen financiero".

    Devuelve totales por departamento + un total global, sin exponer
    filas individuales (para mantener la respuesta compacta).
    """
    por_departamento = (
        df.groupby("Departamento")["Monto_USD"]
        .agg(total_usd="sum", cantidad_transacciones="count")
        .round(2)
        .reset_index()
    )

    resumen_departamentos = [
        {
            "departamento": fila["Departamento"],
            "total_usd": float(fila["total_usd"]),
            "cantidad_transacciones": int(fila["cantidad_transacciones"]),
        }
        for _, fila in por_departamento.iterrows()
    ]

    por_estado = df["Estado_Aprobacion"].value_counts().to_dict()

    return {
        "total_usd_global": round(float(df["Monto_USD"].sum()), 2),
        "cantidad_transacciones_global": int(len(df)),
        "por_departamento": resumen_departamentos,
        "cantidad_por_estado": {k: int(v) for k, v in por_estado.items()},
    }


# ---------------------------------------------------------------------------
# 5. Transacción más alta / más baja
# ---------------------------------------------------------------------------

def transaccion_mas_alta(df: pd.DataFrame) -> dict:
    """
    Pregunta que resuelve: "¿Cuál fue la compra más cara?"
    """
    fila = df.loc[df["Monto_USD"].idxmax()]
    return {"tipo": "mas_alta", "transaccion": _fila_a_dict(fila)}


def transaccion_mas_baja(df: pd.DataFrame) -> dict:
    """
    Pregunta que resuelve: "¿Cuál fue la compra más económica?"
    """
    fila = df.loc[df["Monto_USD"].idxmin()]
    return {"tipo": "mas_baja", "transaccion": _fila_a_dict(fila)}


# ---------------------------------------------------------------------------
# Prueba manual rápida
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    df = cargar_datos_financieros()

    print("=== total_por_departamento('Infraestructura') ===")
    print(json.dumps(total_por_departamento(df, "Infraestructura"), indent=2, ensure_ascii=False))

    print("\n=== total_por_categoria('opex') (minúsculas, prueba normalización) ===")
    print(json.dumps(total_por_categoria(df, "opex"), indent=2, ensure_ascii=False))

    print("\n=== transacciones_por_estado('Rechazado') ===")
    print(json.dumps(transacciones_por_estado(df, "Rechazado"), indent=2, ensure_ascii=False))

    print("\n=== resumen_general() ===")
    print(json.dumps(resumen_general(df), indent=2, ensure_ascii=False))

    print("\n=== transaccion_mas_alta() ===")
    print(json.dumps(transaccion_mas_alta(df), indent=2, ensure_ascii=False))

    print("\n=== transaccion_mas_baja() ===")
    print(json.dumps(transaccion_mas_baja(df), indent=2, ensure_ascii=False))

    print("\n=== departamento inexistente (prueba de manejo de error) ===")
    print(json.dumps(total_por_departamento(df, "Marketing"), indent=2, ensure_ascii=False))