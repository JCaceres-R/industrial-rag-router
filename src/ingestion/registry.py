"""
src/ingestion/registry.py

Este archivo es el "directorio telefónico": recibe la ruta de CUALQUIER
archivo del corpus y decide automáticamente qué función de loaders.py
debe usarse, según la extensión.

Ventaja de tener esto separado: si mañana agregas un documento nuevo
(ej. un .txt), solo agregas una línea aquí. No hay que tocar el router,
ni el RAG, ni los Tools.
"""

from pathlib import Path
from src.ingestion.loaders import load_pdf, load_html, load_tabular, load_json


def load_document(filepath: str):
    """
    Punto de entrada único para cargar cualquier archivo del corpus.

    Devuelve una tupla: (tipo_de_contenido, contenido)

    tipo_de_contenido es uno de:
        "texto"    -> string listo para chunking + RAG (PDF, HTML)
        "tabular"  -> DataFrame de Pandas (CSV, XLSX)
        "json"     -> dict de Python (JSON)

    Este "tipo_de_contenido" es justamente lo que el router (más adelante,
    en src/graph/router.py) usa para saber si algo debe indexarse en el
    vector store o quedarse disponible para un Tool.
    """
    extension = Path(filepath).suffix.lower()

    if extension == ".pdf":
        return "texto", load_pdf(filepath)

    elif extension == ".html":
        return "texto", load_html(filepath)

    elif extension in (".csv", ".xlsx"):
        return "tabular", load_tabular(filepath)

    elif extension == ".json":
        return "json", load_json(filepath)

    else:
        raise ValueError(
            f"No hay loader registrado para archivos con extensión '{extension}'. "
            f"Agrega uno nuevo en loaders.py y regístralo aquí."
        )