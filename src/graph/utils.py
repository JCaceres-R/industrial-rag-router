"""
src/graph/utils.py

Funciones pequeñas compartidas entre nodos del grafo, para no duplicar
lógica.

CORRECCIÓN respecto a la versión anterior: el import de AgentState era
`from state import AgentState` (ruta relativa a la raíz del proyecto),
lo cual rompía con ModuleNotFoundError en cuanto build.py ejecutara el
grafo como paquete real (src.graph.*). Se corrige a `from src.graph.state`,
igual que ya hacían router.py y nodo_respuesta.py.
"""

from __future__ import annotations

import json
import os

from groq import Groq

from src.graph.state import AgentState

# Instancia global única, reutilizada por todos los nodos que hacen
# tool-calling (financiero / telemetria / schema_api). Mismo patrón que
# router.py y nodo_respuesta.py: un solo cliente HTTP por proceso.
CLIENTE_GROQ = Groq()


def extraer_ultima_pregunta(state: AgentState) -> str:
    """
    Toma el texto del último mensaje del historial de forma segura.
    Soporta tanto objetos con atributo .content como diccionarios con clave 'content'.
    Retorna "" si el historial está vacío, no existe o el contenido no se puede obtener.
    """
    mensajes = state.get("messages", [])
    if not mensajes:
        return ""

    ultimo_mensaje = mensajes[-1]

    if hasattr(ultimo_mensaje, "content"):
        return ultimo_mensaje.content or ""

    if isinstance(ultimo_mensaje, dict):
        return ultimo_mensaje.get("content", "")

    return getattr(ultimo_mensaje, "content", "") or ""


def seleccionar_funcion_herramienta(
    pregunta: str,
    herramientas: list[dict],
    prompt_sistema: str,
    modelo: str | None = None,
) -> tuple[str | None, dict]:
    """
    Helper compartido por los 3 nodos de tool (financiero/telemetria/
    schema_api). Envía la pregunta del usuario junto con un catálogo de
    funciones en formato tool-calling de Groq (compatible OpenAI) y
    devuelve el nombre de la función elegida + sus argumentos ya
    parseados desde JSON.

    Se usa tool_choice="required" porque el router YA decidió la rama:
    en este punto sabemos con certeza que el LLM debe elegir alguna
    función del catálogo, no responder en texto libre.

    Costo Groq: 1 llamada corta (max_tokens=200, solo necesitamos el
    nombre de función + argumentos, nunca prosa).

    Devuelve (None, {}) si, por algún motivo, el LLM no devuelve
    tool_calls (defensivo, no debería pasar con tool_choice="required").
    """
    modelo = modelo or os.environ.get("GROQ_MODEL_TOOLS", "openai/gpt-oss-120b")

    respuesta = CLIENTE_GROQ.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": pregunta},
        ],
        tools=herramientas,
        tool_choice="required",
        max_tokens=200,
        temperature=0,
    )

    tool_calls = respuesta.choices[0].message.tool_calls
    if not tool_calls:
        return None, {}

    llamada = tool_calls[0]
    try:
        argumentos = json.loads(llamada.function.arguments)
    except (json.JSONDecodeError, TypeError):
        argumentos = {}

    return llamada.function.name, argumentos