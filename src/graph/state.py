"""
Define el AgentState: la "memoria de trabajo".
"""

from __future__ import annotations
from typing import Annotated, Literal, Optional, TypedDict
from langgraph.graph.message import add_messages

# Las 4 ramas posibles a las que el router puede enviar una pregunta.
Ruta = Literal["rag", "financiero", "telemetria", "schema_api"]

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

    # Clasificación que produce el nodo router. Empieza en None; el
    # nodo router es el único que la escribe.
    ruta: Optional[Ruta]

    # Resultado ya calculado por la rama correspondiente, listo para
    # que el nodo final lo traduzca a lenguaje natural:
    #   - rama 'rag'         -> {"contexto": "<texto formateado de chunks>"}
    #   - rama 'financiero'  -> el dict que devuelve alguna función de
    #                           src/tools/financiero.py
    #   - rama 'telemetria'  -> idem, de src/tools/telemetria.py
    #   - rama 'schema_api'  -> idem, de src/tools/api_schema.py
    # Nunca contiene un DataFrame ni el JSON completo — eso ya se
    # resolvió en la capa de Tools (ver financiero.py/telemetria.py/
    # api_schema.py), aquí solo se transporta el resultado compacto.
    resultado: Optional[dict]