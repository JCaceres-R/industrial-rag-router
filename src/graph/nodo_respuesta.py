"""
src/graph/nodo_respuesta.py

Último nodo del grafo antes de END. Toma lo que ya calculó la rama
correspondiente (contexto RAG o dict de una tool) y le pide al LLM que
lo redacte en lenguaje natural para el usuario — el LLM NO recibe el
DataFrame ni el documento completo, solo lo que ya quedó en
state['resultado'], que es intencionalmente compacto (ver Tools en
src/tools/ y retriever.py).

Costo en llamadas Groq de este nodo: 1 por turno, siempre — es la
última llamada del turno, sin importar la rama.

Presupuesto de tokens: max_tokens acotado (400) para dejar margen
dentro del límite de 8K TPM incluso en el peor caso (rama RAG con
contexto de ~2.6K caracteres, ver validación empírica en
docs del proyecto).
"""

from __future__ import annotations

import json
import os

from groq import Groq
from langchain_core.messages import AIMessage

from src.graph.state import AgentState
from src.graph.utils import extraer_ultima_pregunta

GROQ_MODEL_RESPUESTA = os.environ.get("GROQ_MODEL_RESPUESTA", "openai/gpt-oss-120b")

PROMPTS_SISTEMA_POR_RAMA = {
    "rag": (
        "Eres el asistente técnico de Auvix. Responde la pregunta del "
        "usuario basándote EXCLUSIVAMENTE en el siguiente contexto "
        "extraído de la documentación técnica (manual PID y/o auditoría "
        "de redes). Redacta con tus propias palabras, no copies el "
        "contexto literalmente. Si el contexto no alcanza para responder, "
        "dilo explícitamente en vez de inventar información.\n\n"
        "Contexto:\n{datos}"
    ),
    "financiero": (
        "Eres el asistente financiero de Auvix. Responde la pregunta del "
        "usuario basándote EXCLUSIVAMENTE en el siguiente resultado ya "
        "calculado (formato JSON). No inventes cifras que no estén aquí. "
        "Si 'encontrado' es false, explica la situación al usuario y "
        "menciona las opciones disponibles que sí existen.\n\n"
        "Resultado:\n{datos}"
    ),
    "telemetria": (
        "Eres el asistente de monitoreo IoT de Auvix. Responde la "
        "pregunta del usuario basándote EXCLUSIVAMENTE en el siguiente "
        "resultado ya calculado (formato JSON) sobre los nodos de la "
        "Línea 4. No inventes valores que no estén aquí. Si 'encontrado' "
        "es false, explica la situación y menciona las opciones "
        "disponibles.\n\nResultado:\n{datos}"
    ),
    "schema_api": (
        "Eres el asistente de integración de sistemas de Auvix. Responde "
        "la pregunta del usuario basándote EXCLUSIVAMENTE en el siguiente "
        "resultado ya calculado (formato JSON) sobre el esquema de la API "
        "de sensores. No inventes campos ni endpoints que no estén aquí. "
        "Si 'encontrado' es false, explica la situación y menciona las "
        "opciones disponibles.\n\nResultado:\n{datos}"
    ),
}

# CORRECCIÓN: Instancia global única del cliente para reutilizar el pool de conexiones HTTP
CLIENTE_GROQ = Groq()

def _construir_prompt_sistema(ruta: str, resultado: dict) -> str:
    plantilla = PROMPTS_SISTEMA_POR_RAMA.get(ruta, PROMPTS_SISTEMA_POR_RAMA["rag"])

    if ruta == "rag":
        datos = resultado.get("contexto") or resultado.get("mensaje", "")
    else:
        datos = json.dumps(resultado, ensure_ascii=False, separators=(",", ":"))

    return plantilla.format(datos=datos)


def nodo_respuesta(state: AgentState) -> dict:
    pregunta = extraer_ultima_pregunta(state)
    ruta = state.get("ruta") or "rag"
    resultado = state.get("resultado") or {}

    prompt_sistema = _construir_prompt_sistema(ruta, resultado)

    # CORRECCIÓN: Usar la instancia global reutilizable
    respuesta = CLIENTE_GROQ.chat.completions.create(
        model=GROQ_MODEL_RESPUESTA,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": pregunta},
        ],
        max_tokens=400,
        temperature=0.3,
    )

    texto_respuesta = respuesta.choices[0].message.content
    return {"messages": [AIMessage(content=texto_respuesta)]}