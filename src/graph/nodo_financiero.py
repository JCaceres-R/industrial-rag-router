"""
src/graph/nodo_financiero.py

Nodo de LangGraph dedicado exclusivamente a resolver preguntas financieras.
Utiliza "Tool Calling" nativo de Groq para decidir qué función de Pandas 
(definida en src/tools/financiero.py) debe ejecutarse.
"""

from __future__ import annotations

import os
import json
from groq import Groq

from src.graph.state import AgentState
from src.graph.utils import extraer_ultima_pregunta

# Importamos las funciones reales que construiste
from src.tools.financiero import (
    cargar_datos_financieros,
    total_por_departamento,
    total_por_categoria,
    transacciones_por_estado,
    resumen_general,
    transaccion_mas_alta,
    transaccion_mas_baja
)

# Usamos el modelo rápido para Tool Calling (ej. Qwen 3.6B o Llama 3.1 8B)
GROQ_MODEL_TOOLS = os.environ.get("GROQ_MODEL_TOOLS", "qwen/qwen3.6-27b")
CLIENTE_GROQ = Groq()

# Definición del esquema estricto de las herramientas para que Groq las entienda
HERRAMIENTAS_FINANCIERAS = [
    {
        "type": "function",
        "function": {
            "name": "total_por_departamento",
            "description": "Calcula el gasto total acumulado de un departamento específico.",
            "parameters": {
                "type": "object",
                "properties": {
                    "departamento": {
                        "type": "string",
                        "description": "El nombre del departamento. Ej: Infraestructura, Marketing, Ventas."
                    }
                },
                "required": ["departamento"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "total_por_categoria",
            "description": "Suma el gasto total de una categoría (ej. Hardware, OpEx, Software).",
            "parameters": {
                "type": "object",
                "properties": {
                    "categoria": {
                        "type": "string",
                        "description": "La categoría del gasto."
                    }
                },
                "required": ["categoria"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transacciones_por_estado",
            "description": "Lista las transacciones que están en un estado específico (Aprobado, Pendiente, Rechazado).",
            "parameters": {
                "type": "object",
                "properties": {
                    "estado": {
                        "type": "string",
                        "description": "El estado de la transacción."
                    }
                },
                "required": ["estado"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_general",
            "description": "Devuelve un resumen financiero global, incluyendo el gasto total y un desglose básico por departamento.",
            "parameters": {
                "type": "object",
                "properties": {} # No requiere parámetros
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transaccion_mas_alta",
            "description": "Encuentra la transacción (compra) más cara o costosa de toda la base de datos.",
            "parameters": {
                "type": "object",
                "properties": {} # No requiere parámetros
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "transaccion_mas_baja",
            "description": "Encuentra la transacción (compra) más barata o económica de toda la base de datos.",
            "parameters": {
                "type": "object",
                "properties": {} # No requiere parámetros
            }
        }
    }
]

def nodo_financiero(state: AgentState) -> dict:
    """
    Nodo ejecutor. Lee la pregunta, pide a Groq que elija una herramienta,
    ejecuta el cálculo local con Pandas y devuelve el resultado compacto.
    """
    pregunta = extraer_ultima_pregunta(state)

    # 1. Cargar la base de datos real (o el Mock para tests)
    try:
        df = cargar_datos_financieros()
    except Exception as e:
        return {"resultado": {"encontrado": False, "mensaje": f"Error interno: No se pudo leer el CSV financiero. Detalles: {e}"}}

    # 2. Llamada a Groq solicitando Tool Calling explícito
    respuesta = CLIENTE_GROQ.chat.completions.create(
        model=GROQ_MODEL_TOOLS,
        messages=[
            {"role": "system", "content": "Eres el cerebro analítico de Auvix. Tu único objetivo es leer la pregunta del usuario y seleccionar la herramienta matemática exacta para responderla. No generes respuestas en texto; SOLO invoca herramientas."},
            {"role": "user", "content": pregunta}
        ],
        tools=HERRAMIENTAS_FINANCIERAS,
        tool_choice="auto",
        temperature=0.1
    )

    eleccion_herramienta = respuesta.choices[0].message.tool_calls

    # 3. Manejo de errores si el LLM no supo qué herramienta usar
    if not eleccion_herramienta:
        return {"resultado": {"encontrado": False, "mensaje": "La IA no logró identificar qué métrica financiera calcular basándose en la pregunta."}}

    # 4. Extraer la función y los parámetros que el LLM decidió
    llamada = eleccion_herramienta[0].function
    nombre_funcion = llamada.name
    argumentos = json.loads(llamada.arguments)

    dict_resultado = {}

    # 5. Ejecutar la función real de Python (El enrutamiento interno)
    if nombre_funcion == "total_por_departamento":
        dict_resultado = total_por_departamento(df, argumentos.get("departamento", ""))
        
    elif nombre_funcion == "total_por_categoria":
        dict_resultado = total_por_categoria(df, argumentos.get("categoria", ""))
        
    elif nombre_funcion == "transacciones_por_estado":
        dict_resultado = transacciones_por_estado(df, argumentos.get("estado", ""))
        
    elif nombre_funcion == "resumen_general":
        dict_resultado = resumen_general(df)
        
    elif nombre_funcion == "transaccion_mas_alta":
        dict_resultado = transaccion_mas_alta(df)
        
    elif nombre_funcion == "transaccion_mas_baja":
        dict_resultado = transaccion_mas_baja(df)
        
    else:
        dict_resultado = {"encontrado": False, "mensaje": f"Función no soportada: {nombre_funcion}"}

    # 6. Guardar el resultado en el portafolio (AgentState)
    return {"resultado": dict_resultado}