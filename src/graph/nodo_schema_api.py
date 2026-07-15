"""
src/graph/nodo_schema_api.py

Nodo de LangGraph dedicado a resolver preguntas sobre el esquema de la API de sensores.
Utiliza "Tool Calling" nativo para decidir qué función de consulta técnica 
debe ejecutarse sobre el JSON del esquema.
"""

from __future__ import annotations

import os
import json
from groq import Groq

from src.graph.state import AgentState
from src.graph.utils import extraer_ultima_pregunta

# Importamos las funciones EXACTAS de tu archivo de herramientas reales
# (Asegúrate de que la ruta 'src.tools.api_schema' coincida con donde guardaste tu script)
from src.tools.api_schema import (
    cargar_esquema_api,
    listar_endpoints,
    obtener_esquema_endpoint,
    obtener_ejemplo_payload,
    interpretar_codigo_respuesta,
    buscar_campo
)

GROQ_MODEL_TOOLS = os.environ.get("GROQ_MODEL_TOOLS", "llama-3.1-8b-instant")
CLIENTE_GROQ = Groq()

# Definición del esquema estricto adaptado a TUS funciones reales
HERRAMIENTAS_SCHEMA_API = [
    {
        "type": "function",
        "function": {
            "name": "listar_endpoints",
            "description": "Lista todos los endpoints disponibles en la API de sensores y su descripción general.",
            "parameters": {
                "type": "object",
                "properties": {} 
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_esquema_endpoint",
            "description": "Devuelve la lista de campos, tipos de datos y si son requeridos para un endpoint específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "La ruta o alias del endpoint. Ej: motors, environment, /api/v1/telemetry/motors."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_ejemplo_payload",
            "description": "Proporciona un ejemplo de la estructura JSON (payload) que se debe enviar a un endpoint.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "La ruta o alias del endpoint. Ej: motors, environment."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "interpretar_codigo_respuesta",
            "description": "Explica el significado de un código de estado HTTP específico para un endpoint en particular.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "La ruta del endpoint. Ej: motors."
                    },
                    "status_code": {
                        "type": "integer",
                        "description": "El código HTTP a consultar. Ej: 200, 400, 503."
                    }
                },
                "required": ["path", "status_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "buscar_campo",
            "description": "Busca en qué endpoints de la API se utiliza o aparece un campo específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre_campo": {
                        "type": "string",
                        "description": "El nombre exacto o parcial del campo a buscar. Ej: rpm, status_code."
                    }
                },
                "required": ["nombre_campo"]
            }
        }
    }
]

def nodo_schema_api(state: AgentState) -> dict:
    """
    Nodo ejecutor para la rama de especificación y esquemas de la API.
    """
    pregunta = extraer_ultima_pregunta(state)

    # 1. Cargar el JSON en memoria usando tu función real
    try:
        esquema = cargar_esquema_api()
    except Exception as e:
        return {"resultado": {"encontrado": False, "mensaje": f"Error cargando esquema: {e}"}}

    # 2. Llamada a Groq solicitando Tool Calling explícito
    respuesta = CLIENTE_GROQ.chat.completions.create(
        model=GROQ_MODEL_TOOLS,
        messages=[
            {
                "role": "system", 
                "content": "Eres el orquestador de software de Auvix. Tu objetivo es leer la duda sobre la API y seleccionar la herramienta exacta para resolverla. SOLO invoca herramientas."
            },
            {"role": "user", "content": pregunta}
        ],
        tools=HERRAMIENTAS_SCHEMA_API,
        tool_choice="auto",
        temperature=0.1
    )

    eleccion_herramienta = respuesta.choices[0].message.tool_calls

    if not eleccion_herramienta:
        return {"resultado": {"encontrado": False, "mensaje": "No se logró identificar qué consulta del esquema de la API ejecutar."}}

    # 3. Extraer la función y parámetros seleccionados por el LLM
    llamada = eleccion_herramienta[0].function
    nombre_funcion = llamada.name
    argumentos = json.loads(llamada.arguments)

    dict_resultado = {}

    # 4. Enrutamiento EXACTO a tus funciones de Python
    # Nota: Le pasamos 'esquema' como primer argumento a todas, como lo definiste en tu script
    if nombre_funcion == "listar_endpoints":
        dict_resultado = listar_endpoints(esquema)
        
    elif nombre_funcion == "obtener_esquema_endpoint":
        dict_resultado = obtener_esquema_endpoint(esquema, argumentos.get("path", ""))
        
    elif nombre_funcion == "obtener_ejemplo_payload":
        dict_resultado = obtener_ejemplo_payload(esquema, argumentos.get("path", ""))
        
    elif nombre_funcion == "interpretar_codigo_respuesta":
        # Aseguramos que status_code entre como entero (int)
        codigo = int(argumentos.get("status_code", 0))
        dict_resultado = interpretar_codigo_respuesta(esquema, argumentos.get("path", ""), codigo)
        
    elif nombre_funcion == "buscar_campo":
        dict_resultado = buscar_campo(esquema, argumentos.get("nombre_campo", ""))
        
    else:
        dict_resultado = {"encontrado": False, "mensaje": f"Función no soportada: {nombre_funcion}"}

    # 5. Guardar el resultado en el AgentState
    return {"resultado": dict_resultado}