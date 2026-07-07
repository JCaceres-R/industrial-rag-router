"""
src/graph/nodo_telemetria.py

Nodo de LangGraph dedicado a resolver preguntas sobre la telemetría de los nodos IoT.
Utiliza "Tool Calling" nativo para decidir qué función de Pandas (definida en 
src/tools/telemetria.py) debe ejecutarse para extraer la respuesta del archivo Excel.
"""

from __future__ import annotations

import os
import json
from groq import Groq

from src.graph.state import AgentState
from src.graph.utils import extraer_ultima_pregunta

# Importamos las funciones reales de telemetría
from src.tools.telemetria import (
    cargar_datos_telemetria,
    historico_por_nodo,
    nodos_en_alerta,
    promedio_por_nodo,
    resumen_general,
    lectura_mas_alta,
    lectura_mas_baja
)

GROQ_MODEL_TOOLS = os.environ.get("GROQ_MODEL_TOOLS", "qwen/qwen3.6-27b")
CLIENTE_GROQ = Groq()

# Definición del esquema estricto de las herramientas para Groq
HERRAMIENTAS_TELEMETRIA = [
    {
        "type": "function",
        "function": {
            "name": "historico_por_nodo",
            "description": "Devuelve el estado más reciente y el historial de lecturas de un nodo IoT específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "El identificador exacto del nodo. Ej: NODO-L4-01, NODO-L4-02, NODO-L4-03."
                    }
                },
                "required": ["node_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "nodos_en_alerta",
            "description": "Lista todas las lecturas y nodos que actualmente se encuentran en estado de 'Alerta'.",
            "parameters": {
                "type": "object",
                "properties": {} 
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "promedio_por_nodo",
            "description": "Calcula los promedios históricos de temperatura, consumo y latencia para un nodo específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "El identificador del nodo. Ej: NODO-L4-01."
                    }
                },
                "required": ["node_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_general",
            "description": "Genera un resumen global de toda la red de nodos IoT, incluyendo promedios globales y recuento de alertas.",
            "parameters": {
                "type": "object",
                "properties": {} 
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lectura_mas_alta",
            "description": "Encuentra el registro con el valor más alto para una métrica específica en toda la red.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metrica": {
                        "type": "string",
                        "enum": ["temperatura", "consumo", "latencia"],
                        "description": "La métrica que se desea evaluar."
                    }
                },
                "required": ["metrica"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "lectura_mas_baja",
            "description": "Encuentra el registro con el valor más bajo para una métrica específica en toda la red.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metrica": {
                        "type": "string",
                        "enum": ["temperatura", "consumo", "latencia"],
                        "description": "La métrica que se desea evaluar."
                    }
                },
                "required": ["metrica"]
            }
        }
    }
]

def nodo_telemetria(state: AgentState) -> dict:
    """
    Nodo ejecutor para la rama de telemetría IoT.
    """
    pregunta = extraer_ultima_pregunta(state)

    # 1. Cargar la base de datos de telemetría (XLSX)
    try:
        df = cargar_datos_telemetria()
    except Exception as e:
        return {"resultado": {"encontrado": False, "mensaje": f"Error interno: No se pudo cargar el archivo Excel de telemetría. Detalles: {e}"}}

    # 2. Llamada a Groq solicitando Tool Calling explícito
    respuesta = CLIENTE_GROQ.chat.completions.create(
        model=GROQ_MODEL_TOOLS,
        messages=[
            {
                "role": "system", 
                "content": "Eres el orquestador de la red IoT de Auvix. Tu único objetivo es leer la pregunta del usuario y seleccionar la herramienta de datos exacta para responderla. No generes texto, SOLO invoca herramientas."
            },
            {"role": "user", "content": pregunta}
        ],
        tools=HERRAMIENTAS_TELEMETRIA,
        tool_choice="auto",
        temperature=0.1
    )

    eleccion_herramienta = respuesta.choices[0].message.tool_calls

    if not eleccion_herramienta:
        return {"resultado": {"encontrado": False, "mensaje": "El orquestador no logró identificar qué análisis de red ejecutar basándose en la pregunta."}}

    # 3. Extraer la función y parámetros
    llamada = eleccion_herramienta[0].function
    nombre_funcion = llamada.name
    argumentos = json.loads(llamada.arguments)

    dict_resultado = {}

    # 4. Enrutamiento interno a las funciones de Pandas
    if nombre_funcion == "historico_por_nodo":
        dict_resultado = historico_por_nodo(df, argumentos.get("node_id", ""))
        
    elif nombre_funcion == "nodos_en_alerta":
        dict_resultado = nodos_en_alerta(df)
        
    elif nombre_funcion == "promedio_por_nodo":
        dict_resultado = promedio_por_nodo(df, argumentos.get("node_id", ""))
        
    elif nombre_funcion == "resumen_general":
        dict_resultado = resumen_general(df)
        
    elif nombre_funcion == "lectura_mas_alta":
        dict_resultado = lectura_mas_alta(df, argumentos.get("metrica", ""))
        
    elif nombre_funcion == "lectura_mas_baja":
        dict_resultado = lectura_mas_baja(df, argumentos.get("metrica", ""))
        
    else:
        dict_resultado = {"encontrado": False, "mensaje": f"Función de telemetría no soportada: {nombre_funcion}"}

    # 5. Guardar el resultado en el estado
    return {"resultado": dict_resultado}