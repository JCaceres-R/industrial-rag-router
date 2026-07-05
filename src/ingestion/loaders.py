import json
import pandas as pd
from pypdf import PdfReader
from bs4 import BeautifulSoup


def load_pdf(filepath: str) -> str:
    """
    Extrae el texto plano de un PDF, página por página.

    Devuelve: un solo string con todo el texto del documento.
    Este texto crudo es la ENTRADA del pipeline RAG (todavía no está
    troceado ni vectorizado, eso pasa después en chunking.py).
    """
    reader = PdfReader(filepath)
    texto_completo = []

    for numero_pagina, pagina in enumerate(reader.pages, start=1):
        texto_pagina = pagina.extract_text() or ""
        texto_completo.append(texto_pagina)
    return "\n\n".join(texto_completo)


def load_html(filepath: str) -> str:
    """
    Extrae el texto legible de un HTML, descartando las etiquetas.

    Devuelve: un solo string con el contenido de prosa del documento
    (títulos, párrafos, texto de tablas), sin código HTML.
    Igual que el PDF, este texto crudo alimenta al pipeline RAG.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        contenido_html = f.read()

    soup = BeautifulSoup(contenido_html, "html.parser")
    texto_limpio = soup.get_text(separator="\n", strip=True)

    return texto_limpio


def load_tabular(filepath: str) -> pd.DataFrame:
    """
    Carga un archivo CSV o XLSX como DataFrame de Pandas.

    Devuelve: un DataFrame — NO texto, NO va al vector store.
    Esta función es usada por tools/tabular.py, que se encarga
    de filtrar y calcular sobre estos datos sin nunca mandar
    el DataFrame completo al LLM.
    """
    if filepath.endswith(".csv"):
        return pd.read_csv(filepath)
    elif filepath.endswith(".xlsx"):
        return pd.read_excel(filepath)
    else:
        raise ValueError(f"Formato no soportado para datos tabulares: {filepath}")


def load_json(filepath: str) -> dict:
    """
    Carga un archivo JSON como diccionario de Python.

    Devuelve: un dict — tampoco va al vector store.
    Es usado por tools/api_schema.py para responder preguntas
    sobre la estructura de la API consultando el dict directamente.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)