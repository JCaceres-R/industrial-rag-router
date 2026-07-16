"""
src/graph/nodo_rag.py

Nodo de la rama 'rag' del grafo. A diferencia de los nodos de tool
(financiero/telemetria/schema_api), este NO usa tool-calling de Groq:
es una secuencia fija de pasos sin parámetros que el LLM deba elegir
(ver docs/CORPUS.md — la pregunta ya está en el estado, no hay nada
que "decidir" aquí más que ejecutar la búsqueda semántica).

Flujo: pregunta -> vectorizar -> buscar top-k en FAISS -> formatear
contexto -> guardar en state['resultado'] para que nodo_respuesta.py
lo inyecte en el prompt final.

Costo en llamadas Groq de este nodo: CERO. La vectorización de la
pregunta usa el mismo modelo local de sentence-transformers que los
chunks (paraphrase-multilingual-MiniLM-L12-v2), no consume cuota de
Groq ni cuenta para el límite de TPM/RPM.

CORRECCIÓN (memoria en Render/512MB): antes, buscar_chunks_relevantes()
se llamaba sin pasar 'modelo', así que cada pregunta RAG disparaba una
carga completa y nueva de SentenceTransformer (PyTorch + pesos del
modelo) desde cero. Ahora se pasa explícitamente el singleton cacheado
obtener_modelo_embeddings(), que carga el modelo UNA sola vez por
proceso y reutiliza esa misma instancia en cada pregunta siguiente.
"""

from __future__ import annotations

import os
from src.graph.state import AgentState
from src.graph.utils import extraer_ultima_pregunta
from src.rag.retriever import buscar_chunks_relevantes, formatear_contexto
from src.rag.vectorstore import obtener_modelo_embeddings

# Carpeta donde vectorstore.py persistió el índice FAISS + chunks.json.
CARPETA_VECTORSTORE = os.environ.get("CARPETA_VECTORSTORE", "data/vectorstore")

# k=3 y distancia_maxima=None por defecto, tal como se validó en
# retriever.py. Se centraliza acá para poder ajustarlo sin tocar el
# resto del grafo.
K_CHUNKS = int(os.environ.get("RAG_K_CHUNKS", "3"))
DISTANCIA_MAXIMA = os.environ.get("RAG_DISTANCIA_MAXIMA")
DISTANCIA_MAXIMA = float(DISTANCIA_MAXIMA) if DISTANCIA_MAXIMA else None


def nodo_rag(state: AgentState) -> dict:
    """
    Nodo de LangGraph para la rama RAG. Devuelve solo la clave
    'resultado' LangGraph fusiona esto con el resto del AgentState.
    """
    pregunta = extraer_ultima_pregunta(state)

    chunks_relevantes = buscar_chunks_relevantes(
        pregunta=pregunta,
        carpeta_vectorstore=CARPETA_VECTORSTORE,
        k=K_CHUNKS,
        modelo=obtener_modelo_embeddings(),  # singleton: no recarga en cada pregunta
        distancia_maxima=DISTANCIA_MAXIMA,
    )

    if not chunks_relevantes:
        # Caso explícito de "sin información relevante" — el nodo de
        # respuesta final debe poder decir "no encontré esto en la
        # documentación" en vez de alucinar con un contexto vacío.
        return {
            "resultado": {
                "encontrado": False,
                "contexto": "",
                "cantidad_chunks": 0,
                "mensaje": "No se encontraron fragmentos relevantes en el manual técnico ni en la auditoría de redes.",
            }
        }

    contexto_formateado = formatear_contexto(chunks_relevantes)

    return {
        "resultado": {
            "encontrado": True,
            "contexto": contexto_formateado,
            "cantidad_chunks": len(chunks_relevantes),
        }
    }