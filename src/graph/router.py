"""
src/graph/router.py

Nodo router del grafo: clasifica la última pregunta del usuario en una
de 4 ramas (rag / financiero / telemetria / schema_api) usando una
única llamada a Groq con un prompt de clasificación deliberadamente pequeño.
"""

from __future__ import annotations

import os
from typing import cast

from groq import Groq

from src.graph.state import AgentState, Ruta
from src.graph.utils import extraer_ultima_pregunta

GROQ_MODEL_ROUTER = os.environ.get("GROQ_MODEL_ROUTER", "qwen/qwen3.6-27b")

RAMAS_VALIDAS: tuple[Ruta, ...] = ("rag", "financiero", "telemetria", "schema_api")


PROMPT_SISTEMA_ROUTER = f"""Eres un clasificador de preguntas para un agente corporativo de Auvix.
Clasifica la pregunta del usuario en EXACTAMENTE una de estas 4 categorías,
y responde ÚNICAMENTE con la palabra de la categoría, sin explicación:

rag: preguntas sobre el manual técnico de PID y lazos de control, o
sobre la auditoría de redes/protocolos de comunicación de planta
(temas de prosa técnica, "cómo funciona", "qué dice el manual sobre...").

financiero: preguntas sobre gastos, transacciones, montos en USD,
departamentos, categorías de compra (Hardware/OpEx), o estado de
aprobación de compras (Aprobado/Pendiente/Rechazado).

telemetria: preguntas sobre nodos IoT de la Línea 4 (NODO-L4-01/02/03),
temperatura, consumo eléctrico, latencia, o si un nodo está en alerta.

schema_api: preguntas sobre el esquema de la API de sensores, endpoints,
campos de un payload, códigos de respuesta HTTP, o formato de datos
que se envían a la API.

Responde solo con una de estas palabras: {", ".join(RAMAS_VALIDAS)}"""

CLIENTE_GROQ = Groq()


def _parsear_ruta(texto_respuesta: str) -> Ruta:
    """
    Normaliza la respuesta cruda del LLM a una de las 4 ramas válidas.
    Si el LLM devuelve algo inesperado, se usa 'rag' como fallback
    seguro: es la rama que menos asume sobre estructura de datos, y en
    el peor caso el retriever simplemente no encuentra chunks relevantes.
    """
    limpio = texto_respuesta.strip().lower().strip(".").strip()
    for rama in RAMAS_VALIDAS:
        if rama in limpio:
            return cast(Ruta, rama)
    return "rag"


def nodo_router(state: AgentState) -> dict:
    """
    Nodo de LangGraph. Recibe el estado completo y devuelve únicamente
    la clave 'ruta' con la rama clasificada. LangGraph fusiona el resto
    del estado automáticamente.
    """
    pregunta = extraer_ultima_pregunta(state)

    if not pregunta:
        return {"ruta": "rag"}

    respuesta = CLIENTE_GROQ.chat.completions.create(
        model=GROQ_MODEL_ROUTER,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA_ROUTER},
            {"role": "user", "content": pregunta},
        ],
        max_tokens=10,
        temperature=0,
    )

    ruta = _parsear_ruta(respuesta.choices[0].message.content)
    return {"ruta": ruta}


def enrutar_siguiente_nodo(state: AgentState) -> Ruta:
    """
    Función de arista condicional para add_conditional_edges.
    Se ejecuta después de nodo_router; devuelve la rama a la que
    saltar. Garantiza un valor válido incluso si la clave 'ruta'
    no estuviera presente.
    """
    return state.get("ruta") or "rag"