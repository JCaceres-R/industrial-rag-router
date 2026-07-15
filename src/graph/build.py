"""
src/graph/build.py

Ensambla el StateGraph completo del agente, con la forma exacta del
diagrama acordado:

    __start__ -> router -> (rag | financiero | telemetria | schema_api)
            -> nodo_respuesta -> __end__

Nodos y aristas:
- 'router' es el único punto de entrada. Usa una arista CONDICIONAL
    (add_conditional_edges) porque el siguiente nodo depende del
    resultado de la clasificación (state['ruta']), no es fijo.
- Las 4 ramas de datos (rag/financiero/telemetria/schema_api) usan
    aristas NORMALES (add_edge) hacia 'nodo_respuesta', porque ahí no
    hay decisión que tomar: siempre convergen al mismo nodo final.
- 'nodo_respuesta' -> END también es una arista normal: siempre
    termina el turno ahí.

Memoria de sesión (checkpointer):
Se usa SqliteSaver, persistente en un archivo (data/memoria_sesiones.db
por defecto). Importante porque la capa
Always Free puede reiniciar la VM sin aviso. La conexión se abre una
sola vez al importar este módulo (ver CHECKPOINTER más abajo), no en
cada turno de conversación.

"""

from __future__ import annotations

import os
import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph

from src.graph.state import AgentState
from src.graph.router import nodo_router, enrutar_siguiente_nodo
from src.graph.nodo_rag import nodo_rag
from src.graph.nodo_respuesta import nodo_respuesta

from src.graph.nodo_financiero import nodo_financiero
from src.graph.nodo_telemetria import nodo_telemetria
from src.graph.nodo_schema_api import nodo_schema_api


def construir_grafo() -> StateGraph:
    """
    Registra los 6 nodos y las aristas, y devuelve el StateGraph SIN
    compilar (útil para tests que quieran inspeccionar la estructura
    antes de compilarla con un checkpointer específico).
    """
    grafo = StateGraph(AgentState)

    # --- Registro de nodos ---
    grafo.add_node("router", nodo_router)
    grafo.add_node("nodo_rag", nodo_rag)
    grafo.add_node("nodo_financiero", nodo_financiero)
    grafo.add_node("nodo_telemetria", nodo_telemetria)
    grafo.add_node("nodo_schema_api", nodo_schema_api)
    grafo.add_node("nodo_respuesta", nodo_respuesta)

    # --- Punto de entrada ---
    grafo.add_edge(START, "router")

    # --- Arista condicional: el router decide la rama en tiempo real ---
    # El dict de la derecha traduce el valor devuelto por
    # enrutar_siguiente_nodo(state) (uno de 'rag'/'financiero'/
    # 'telemetria'/'schema_api') al NOMBRE DE NODO registrado arriba.
    # Se hace explícito en vez de asumir que coinciden 1:1, porque los
    # nombres de nodo llevan el prefijo 'nodo_' y los valores de ruta no.
    grafo.add_conditional_edges(
        "router",
        enrutar_siguiente_nodo,
        {
            "rag": "nodo_rag",
            "financiero": "nodo_financiero",
            "telemetria": "nodo_telemetria",
            "schema_api": "nodo_schema_api",
        },
    )

    # --- Las 4 ramas convergen siempre en nodo_respuesta ---
    grafo.add_edge("nodo_rag", "nodo_respuesta")
    grafo.add_edge("nodo_financiero", "nodo_respuesta")
    grafo.add_edge("nodo_telemetria", "nodo_respuesta")
    grafo.add_edge("nodo_schema_api", "nodo_respuesta")

    # --- Fin del turno ---
    grafo.add_edge("nodo_respuesta", END)

    return grafo


# Checkpointer de memoria de sesión, persistente en disco (SqliteSaver).
# Se usa una conexión directa (no el context manager from_conn_string)
# porque esta app vive todo el tiempo que corre el proceso de Streamlit
#  un 'with' cerraría la conexión apenas termina este módulo, y el
# checkpointer quedaría inutilizable en el primer turno de verdad.
#
# check_same_thread=False: Streamlit puede servir requests desde threads
# distintos al que crea la conexión; sqlite3 la bloquea por defecto.
# SqliteSaver serializa el acceso internamente, así que es seguro acá.
RUTA_DB_MEMORIA = os.environ.get("RUTA_DB_MEMORIA", "data/memoria_sesiones.db")
os.makedirs(os.path.dirname(RUTA_DB_MEMORIA) or ".", exist_ok=True)

_CONEXION_SQLITE = sqlite3.connect(RUTA_DB_MEMORIA, check_same_thread=False)
CHECKPOINTER = SqliteSaver(_CONEXION_SQLITE)


def crear_app():
    """
    Compila el grafo con el checkpointer y devuelve la app lista para
    invocar. Separado de construir_grafo() para poder testear la
    estructura del grafo sin necesidad de compilarlo cada vez.
    """
    grafo = construir_grafo()
    return grafo.compile(checkpointer=CHECKPOINTER)


if __name__ == "__main__":
    app = crear_app()
    print(app.get_graph().draw_ascii())