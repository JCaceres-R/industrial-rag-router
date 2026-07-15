"""
tests/test_grafo_integracion.py

Test de INTEGRACIÓN del grafo completo (StateGraph ya compilado con
checkpointer), a diferencia de los tests anteriores que probaban cada
módulo por separado (loaders, chunking, tools, etc).

Qué valida:
    1. Que crear_app() compila sin errores (grafo + SqliteSaver).
    2. Que cada una de las 4 ramas (rag/financiero/telemetria/schema_api)
       se enruta correctamente a partir de una pregunta en lenguaje natural.
    3. Que el nodo de respuesta final siempre entrega un mensaje de texto
       no vacío, sin importar la rama.
    4. Que la memoria de sesión funciona: dos turnos con el mismo
       thread_id comparten historial (LangGraph debe recordar el turno 1
       al procesar el turno 2).

IMPORTANTE: este test SÍ consume cuota real de Groq (cada pregunta
dispara al menos 2 llamadas: router + nodo_respuesta, y las ramas de
tool-calling agregan 1 llamada más). Con 5 preguntas de prueba estamos
muy por debajo del límite de 30 RPM, pero evita correrlo en un loop.
"""

import os
import sys

# 1. Configurar el path para que Python encuentre la carpeta 'src'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from src.graph.build import crear_app
from src.graph.state import Ruta

# ---------------------------------------------------------------------------
# Preguntas de prueba: una por cada rama, redactadas en lenguaje natural
# para forzar al router a clasificar por semántica, no por keywords obvias.
# ---------------------------------------------------------------------------

CASOS_DE_PRUEBA: list[tuple[str, Ruta]] = [
    (
        "¿Cómo se calcula la ganancia crítica en el método de Ziegler-Nichols?",
        "rag",
    ),
    (
        "¿Cuánto se ha gastado en total en el departamento de Infraestructura?",
        "financiero",
    ),
    (
        "¿Cuál es la temperatura promedio del NODO-L4-01?",
        "telemetria",
    ),
    (
        "¿Qué campos son obligatorios en el payload del endpoint de motores?",
        "schema_api",
    ),
]


def _extraer_texto_respuesta(estado_final: dict) -> str:
    """
    El último mensaje en state['messages'] es el AIMessage que produjo
    nodo_respuesta.py. Se aísla aquí porque el objeto exacto (AIMessage
    vs dict) puede variar según cómo LangGraph serialice el checkpoint.
    """
    mensajes = estado_final.get("messages", [])
    if not mensajes:
        return ""
    ultimo = mensajes[-1]
    return getattr(ultimo, "content", "") or ultimo.get("content", "") if isinstance(ultimo, dict) else getattr(ultimo, "content", "")


def probar_compilacion_del_grafo():
    print("[SETUP] Compilando el grafo con crear_app()...")
    app = crear_app()
    print("Éxito: el grafo compiló sin errores (nodos + checkpointer OK).\n")
    return app


def probar_las_4_ramas(app):
    print("=" * 70)
    print("PRUEBA: Enrutamiento correcto de las 4 ramas")
    print("=" * 70)

    resultados = []

    for i, (pregunta, rama_esperada) in enumerate(CASOS_DE_PRUEBA, start=1):
        thread_id = f"test-rama-{i}"
        config = {"configurable": {"thread_id": thread_id}}

        print(f"\n--- Caso {i}: rama esperada = '{rama_esperada}' ---")
        print(f"Pregunta: {pregunta}")

        try:
            estado_final = app.invoke(
                {"messages": [("user", pregunta)]},
                config=config,
            )
        except Exception as e:
            print(f"❌ Error al invocar el grafo: {e}")
            resultados.append(False)
            continue

        ruta_obtenida = estado_final.get("ruta")
        texto_respuesta = _extraer_texto_respuesta(estado_final)

        rama_ok = ruta_obtenida == rama_esperada
        respuesta_ok = bool(texto_respuesta and texto_respuesta.strip())

        print(f"Ruta clasificada por el router: '{ruta_obtenida}' "
              f"({'✅ correcta' if rama_ok else '❌ NO coincide con la esperada'})")
        print(f"Respuesta generada ({'✅ no vacía' if respuesta_ok else '❌ VACÍA'}):")
        print(f"  {texto_respuesta[:300]}{'...' if len(texto_respuesta) > 300 else ''}")

        resultados.append(rama_ok and respuesta_ok)

    return resultados


def probar_memoria_de_sesion(app):
    print("\n" + "=" * 70)
    print("PRUEBA: Memoria de sesión (SqliteSaver) entre turnos")
    print("=" * 70)

    thread_id = "test-memoria-1"
    config = {"configurable": {"thread_id": thread_id}}

    # Turno 1: se establece contexto
    pregunta_1 = "¿Cuánto se gastó en la categoría Hardware?"
    print(f"\n[Turno 1] {pregunta_1}")
    estado_1 = app.invoke({"messages": [("user", pregunta_1)]}, config=config)
    print(f"Respuesta: {_extraer_texto_respuesta(estado_1)[:200]}...")

    # Turno 2: pregunta que depende del historial (referencia implícita)
    pregunta_2 = "¿Y en la categoría OpEx?"
    print(f"\n[Turno 2] {pregunta_2}")
    estado_2 = app.invoke({"messages": [("user", pregunta_2)]}, config=config)
    print(f"Respuesta: {_extraer_texto_respuesta(estado_2)[:200]}...")

    cantidad_mensajes = len(estado_2.get("messages", []))
    # Esperamos al menos 4 mensajes acumulados: user1, ai1, user2, ai2
    memoria_ok = cantidad_mensajes >= 4

    print(f"\nMensajes acumulados en el thread '{thread_id}': {cantidad_mensajes} "
          f"({'✅ el historial se está persistiendo' if memoria_ok else '❌ el historial NO se acumuló como se esperaba'})")

    return memoria_ok


def ejecutar_pruebas():
    print("INICIANDO PRUEBAS DE INTEGRACIÓN: GRAFO COMPLETO (LangGraph)")
    print("-" * 70)

    app = probar_compilacion_del_grafo()

    resultados_ramas = probar_las_4_ramas(app)
    resultado_memoria = probar_memoria_de_sesion(app)

    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    for i, (pregunta, rama_esperada) in enumerate(CASOS_DE_PRUEBA):
        estado = "✅ PASÓ" if resultados_ramas[i] else "❌ FALLÓ"
        print(f"  Rama '{rama_esperada}': {estado}")
    print(f"  Memoria de sesión: {'✅ PASÓ' if resultado_memoria else '❌ FALLÓ'}")

    todo_ok = all(resultados_ramas) and resultado_memoria
    print("\n" + ("🎉 TODAS LAS PRUEBAS PASARON" if todo_ok else "⚠️  HAY PRUEBAS FALLIDAS — revisar detalle arriba"))


if __name__ == "__main__":
    ejecutar_pruebas()