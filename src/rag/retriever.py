"""
Recibe la PREGUNTA del usuario
(texto libre, en lenguaje natural) y devuelve los chunks más relevantes
ya guardados en el vectorstore.

Flujo de este archivo:
    pregunta del usuario (texto)
        -> se convierte en vector (mismo modelo que usamos para los chunks)
        -> FAISS busca los vectores más cercanos
        -> se traducen esas posiciones de vuelta a texto legible (chunks.json)
        -> se devuelven los top-k chunks como texto plano
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from src.rag.vectorstore import cargar_vectorstore, cargar_modelo_embeddings


def buscar_chunks_relevantes(
    pregunta: str,
    carpeta_vectorstore: str,
    k: int = 3,
    modelo: SentenceTransformer = None,
    distancia_maxima: float = None,
) -> list[str]:
    """
    Dada una pregunta, devuelve los k chunks de texto más relevantes.

    Parámetros:
        pregunta: la pregunta del usuario, en texto libre.
        carpeta_vectorstore: carpeta donde están guardados index.faiss y chunks.json
                (la misma que se usó en construir_vectorstore()).
        k: cuántos chunks devolver como máximo. 3 es un buen punto de partida:
        suficiente contexto sin arriesgar el límite de tokens de Groq.
        modelo: instancia ya cargada de SentenceTransformer. Si no se pasa,
                se carga una nueva (en el pipeline real conviene reutilizar
                una sola instancia cargada al arrancar la app, no una por consulta).
        distancia_maxima: umbral opcional. FAISS SIEMPRE devuelve k resultados,
                aunque ninguno tenga relación real con la pregunta (simplemente
                trae "los menos lejanos" de todo el índice). Si se pasa este
                parámetro, se descartan los chunks cuya distancia supere el
                umbral útil para preguntas fuera de tema, donde es mejor
                admitir "no tengo información" que inventar con chunks irrelevantes.

    Devuelve:
        Una lista de strings los chunks relevantes, en orden de cercanía
        (el primero es el más parecido a la pregunta). Puede tener menos de
        k elementos si se aplicó distancia_maxima y algunos quedaron filtrados.
    """
    if modelo is None:
        modelo = cargar_modelo_embeddings()

    indice, chunks = cargar_vectorstore(carpeta_vectorstore)

    # Convertimos la pregunta en un vector, igual que hicimos con cada chunk.
    # encode() espera una lista, por eso [pregunta] entre corchetes.
    vector_pregunta = modelo.encode([pregunta])
    vector_pregunta = np.array(vector_pregunta).astype("float32")

    distancias, posiciones = indice.search(vector_pregunta, k)

    chunks_relevantes = []
    for distancia, posicion in zip(distancias[0], posiciones[0]):
        if distancia_maxima is not None and distancia > distancia_maxima:
            continue
        chunks_relevantes.append(chunks[posicion])

    return chunks_relevantes


def formatear_contexto(chunks_relevantes: list[str]) -> str:
    """
    Une los chunks recuperados en un solo bloque de texto, listo para
    insertarse en el prompt del LLM.

    Se separa en su propia función porque el formato exacto (con o sin
    numeración, con o sin separadores) es algo que probablemente ajustemos
    al construir el nodo RAG del grafo -- mejor tenerlo aislado aquí.
    """
    bloques = [f"[Fragmento {i+1}]\n{chunk}" for i, chunk in enumerate(chunks_relevantes)]
    return "\n\n".join(bloques)