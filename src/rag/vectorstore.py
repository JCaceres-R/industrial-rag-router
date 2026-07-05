"""
src/rag/vectorstore.py

Este archivo hace dos cosas, en este orden:
1. Convierte cada chunk de texto en un vector (usando un modelo de
   embeddings ya entrenado, NO entrenamos nada nosotros).
2. Guarda esos vectores en un índice FAISS para poder buscarlos rápido
   más adelante, cuando llegue una pregunta del usuario.

Este archivo NO llama a Groq. El modelo de embeddings corre localmente,
gratis, sin consumir tu cuota de tokens del LLM.
"""

import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Modelo de embeddings pre-entrenado, liviano, multilingüe.
# Corre localmente (se descarga una vez, ~90MB, y luego funciona sin internet).
NOMBRE_MODELO_EMBEDDINGS = "paraphrase-multilingual-MiniLM-L12-v2"


def cargar_modelo_embeddings() -> SentenceTransformer:
    """
    Carga el modelo de embeddings en memoria.

    Se separa en su propia función porque cargar el modelo es "costoso"
    (tarda unos segundos). Conviene cargarlo UNA vez y reutilizarlo,
    no volver a llamarlo cada vez que se procesa un documento.
    """
    return SentenceTransformer(NOMBRE_MODELO_EMBEDDINGS)


def construir_vectorstore(chunks: list[str], carpeta_destino: str, modelo: SentenceTransformer = None) -> None:
    """
    Convierte una lista de chunks en vectores y los guarda en disco.

    Parámetros:
        chunks: lista de fragmentos de texto (lo que devuelve chunking.chunk_text()).
        carpeta_destino: dónde se guarda el índice FAISS y los textos originales.
        modelo: instancia ya cargada de SentenceTransformer. Si no se pasa,
                se carga una nueva (útil para pruebas rápidas, pero en el
                pipeline real conviene reutilizar un modelo ya cargado).

    Guarda dos archivos en carpeta_destino:
        - index.faiss   -> los vectores (lo que FAISS usa para buscar)
        - chunks.json   -> los textos originales, EN EL MISMO ORDEN que los
                           vectores, porque FAISS solo devuelve números de
                           posición, no el texto en sí. Este archivo es
                           el "traductor" de vuelta a texto legible.
    """
    if modelo is None:
        modelo = cargar_modelo_embeddings()

    # encode() convierte cada string en un vector de números (un embedding).
    embeddings = modelo.encode(chunks, show_progress_bar=False)
    embeddings = np.array(embeddings).astype("float32")  # FAISS requiere float32

    dimension = embeddings.shape[1]  # cuántos números tiene cada vector

    # IndexFlatL2: el tipo de índice más simple de FAISS.
    # Busca por distancia euclidiana ("qué tan cerca" está un vector de otro).
    # Para un corpus pequeño como el tuyo (decenas de chunks), es más que suficiente.
    indice = faiss.IndexFlatL2(dimension)
    indice.add(embeddings)

    os.makedirs(carpeta_destino, exist_ok=True)

    faiss.write_index(indice, os.path.join(carpeta_destino, "index.faiss"))

    with open(os.path.join(carpeta_destino, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)


def cargar_vectorstore(carpeta_origen: str):
    """
    Carga un índice FAISS ya construido, junto con sus textos originales.

    Devuelve:
        (indice, chunks) -> el índice FAISS listo para buscar, y la lista
        de textos originales en el mismo orden que los vectores.

    Esta función es la que usará retriever.py (el siguiente módulo) para
    no tener que reconstruir el vectorstore cada vez que llega una pregunta.
    """
    indice = faiss.read_index(os.path.join(carpeta_origen, "index.faiss"))

    with open(os.path.join(carpeta_origen, "chunks.json"), "r", encoding="utf-8") as f:
        chunks = json.load(f)

    return indice, chunks