"""
src/graph/nodo_schema_api.py

Nodo de LangGraph dedicado a resolver preguntas sobre el esquema de la API de sensores.
Utiliza "Tool Calling" nativo para decidir qué función de consulta técnica 
(definida en src/tools/api_schema.py) debe ejecutarse sobre el JSON del esquema.
"""

from __future__ import annotations

import os
import json
from groq import Groq

from src.graph.state import AgentState
from src.graph.utils import extraer_ultima_pregunta

# Importamos las funciones reales para inspeccionar el esquema de la API
from src.tools.api_schema import (
    cargar_esquema_api,
    obtener_info_endpoint,
    listar_endpoints_por_metodo,
    obtener_campos_payload,
    obtener_codigos_respuesta,
    resumen_completo_api
)

GROQ_MODEL_TOOLS = os.environ.get("GROQ_MODEL_TOOLS", "llama-3.1-8b-instant")
CLIENTE_GROQ = Groq()

# Definición del esquema estricto de las herramientas para Groq
HERRAMIENTAS_SCHEMA_API = [
    {
        "type": "function",
        "function": {
            "name": "obtener_info_endpoint",
            "description": "Devuelve la información detallada de un endpoint específico (descripción, método, parámetros).",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {
                        "type": "string",
                        "description": "La ruta exacta del endpoint. Ej: /api/v1/sensors, /api/v1/sensors/alerts."
                    }
                },
                "required": ["endpoint"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "listar_endpoints_por_metodo",
            "description": "Filtra y lista todos los endpoints que utilizan un método HTTP específico (GET, POST, PUT, DELETE).",
            "parameters": {
                "type": "object",
                "properties": {
                    "metodo": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE"],
                        "description": "El método HTTP en mayúsculas."
                    }
                },
                "required": ["metodo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_campos_payload",
            "description": "Muestra la estructura, campos obligatorios y tipos de datos requeridos en el cuerpo (body/payload) de una petición.",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {
                        "type": "string",
                        "description": "La ruta del endpoint que recibe el payload. Ej: /api/v1/sensors."
                    }
                },
                "required": ["endpoint"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_codigos_respuesta",
            "description": "Lista los códigos de estado HTTP (200, 400, 500, etc.) que puede retornar un endpoint y qué significa cada uno.",
            "parameters": {
                "type": "object",
                "properties": {
                    "endpoint": {
                        "type": "string",
                        "description": "La ruta exacta del endpoint a consultar."
                    }
                },
                "required": ["endpoint"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_completo_api",
            "description": "Genera un mapeo global e índice general de toda la documentación de la API disponible.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

def nodo_schema_api(state: AgentState) -> dict:
    """
    Nodo ejecutor para la rama de especificación y esquemas de la API.
    """
    pregunta = extraer_ultima_pregunta(state)

    # 1. Cargar el archivo de especificación técnica de la API (JSON/Dict)
    try:
        esquema = cargar_esquema_api()
    except Exception as e:
        return {"resultado": {"encontrado": False, "mensaje": f"Error interno: No se pudo cargar el archivo del esquema de la API. Detalles: {e}"}}

    # 2. Llamada a Groq solicitando Tool Calling explícito
    respuesta = CLIENTE_GROQ.chat.completions.create(
        model=GROQ_MODEL_TOOLS,
        messages=[
            {
                "role": "system", 
                "content": "Eres el arquitecto de software de Auvix. Tu único objetivo es inspeccionar la duda del desarrollador y seleccionar la herramienta de consulta de API exacta para resolverla. No inventes texto, SOLO invoca herramientas."
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

    # 4. Enrutamiento e invocación de la lógica de procesamiento local
    if nombre_funcion == "obtener_info_endpoint":
        dict_resultado = obtener_info_endpoint(esquema, argumentos.get("endpoint", ""))
        
    elif nombre_funcion == "listar_endpoints_por_metodo":
        dict_resultado = listar_endpoints_por_metodo(esquema, argumentos.get("metodo", ""))
        
    elif nombre_funcion == "obtener_campos_payload":
        dict_resultado = obtener_campos_payload(esquema, argumentos.get("endpoint", ""))
        
    elif nombre_funcion == "obtener_codigos_respuesta":
        dict_resultado = obtener_codigos_respuesta(esquema, argumentos.get("endpoint", ""))
        
    elif nombre_funcion == "resumen_completo_api":
        dict_resultado = resumen_completo_api(esquema)
        
    else:
        dict_resultado = {"encontrado": False, "mensaje": f"Función de esquema API no soportada: {nombre_funcion}"}

    # 5. Guardar el resultado estructurado en el AgentState
    return {"resultado": dict_resultado}