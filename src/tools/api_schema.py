"""
Tool determinista sobre el esquema de API de sensores IoT de Auvix
(IntegracionDeSistemas_Auvix.json).
cada función "aplana" la parte relevante
del schema a un dict compacto antes de devolverla.

Esquema real verificado (2 endpoints):
    POST /api/v1/telemetry/motors      -> telemetría de motores
    POST /api/v1/telemetry/environment -> telemetría ambiental
"""

from __future__ import annotations
import unicodedata
from src.ingestion.loaders import load_json
RUTA_JSON_POR_DEFECTO = "data/raw/IntegracionDeSistemas_Auvix.json"


# ---------------------------------------------------------------------------
# Utilidades internas
# ---------------------------------------------------------------------------

def _normalizar(texto: str) -> str:
    """Normaliza texto para comparaciones insensibles a mayúsculas/acentos."""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in texto if not unicodedata.combining(c))


def cargar_esquema_api(filepath: str = RUTA_JSON_POR_DEFECTO) -> dict:
    """Carga el JSON de esquema de API como diccionario, vía la capa de ingesta."""
    return load_json(filepath)


def _buscar_endpoint(data: dict, path: str) -> dict | None:
    """
    Busca un endpoint por su 'path', permitiendo coincidencia flexible:
    el LLM puede recibir del usuario 'motors', '/api/v1/telemetry/motors'
    o 'telemetry/motors' — todas deben resolver al mismo endpoint.
    """
    alias = _normalizar(path)
    for endpoint in data["endpoints"]:
        if alias in _normalizar(endpoint["path"]):
            return endpoint
    return None


def _propiedades_aplanadas(endpoint: dict) -> list[dict]:
    """
    Aplana 'request.body.schema.properties' (JSON Schema anidado) a una
    lista simple de dicts con solo lo que el LLM necesita para explicar
    o validar un campo: nombre, tipo, descripción, si es requerido,
    y el valor de ejemplo.
    """
    schema = endpoint["request"]["body"]["schema"]
    requeridos = set(schema.get("required", []))
    propiedades = schema.get("properties", {})

    resultado = []
    for nombre_campo, detalle in propiedades.items():
        resultado.append(
            {
                "campo": nombre_campo,
                "tipo": detalle.get("type"),
                "descripcion": detalle.get("description"),
                "requerido": nombre_campo in requeridos,
                "ejemplo": detalle.get("example"),
            }
        )
    return resultado


def _endpoints_disponibles(data: dict) -> list[str]:
    return [e["path"] for e in data["endpoints"]]


# ---------------------------------------------------------------------------
# 1. Listar endpoints disponibles
# ---------------------------------------------------------------------------

def listar_endpoints(data: dict) -> dict:
    """
    Pregunta que resuelve: "¿Qué endpoints tiene la API de sensores?"
    """
    endpoints = [
        {
            "path": e["path"],
            "method": e["method"],
            "descripcion": e["description"],
        }
        for e in data["endpoints"]
    ]
    return {
        "api_name": data.get("api_name"),
        "version": data.get("version"),
        "cantidad_endpoints": len(endpoints),
        "endpoints": endpoints,
    }


# ---------------------------------------------------------------------------
# 2. Esquema (campos) de un endpoint
# ---------------------------------------------------------------------------

def obtener_esquema_endpoint(data: dict, path: str) -> dict:
    """
    Pregunta que resuelve: "¿Qué campos necesito enviar al endpoint de
    motores?" / "¿Qué es obligatorio en el payload de environment?"
    """
    endpoint = _buscar_endpoint(data, path)
    if endpoint is None:
        return {
            "encontrado": False,
            "path_consultado": path,
            "mensaje": f"No existe un endpoint que coincida con '{path}'.",
            "endpoints_disponibles": _endpoints_disponibles(data),
        }

    return {
        "encontrado": True,
        "path": endpoint["path"],
        "method": endpoint["method"],
        "descripcion": endpoint["description"],
        "campos": _propiedades_aplanadas(endpoint),
    }


# ---------------------------------------------------------------------------
# 3. Ejemplo de payload de un endpoint
# ---------------------------------------------------------------------------

def obtener_ejemplo_payload(data: dict, path: str) -> dict:
    """
    Pregunta que resuelve: "Dame un ejemplo de payload para el endpoint
    de telemetría ambiental."
    """
    endpoint = _buscar_endpoint(data, path)
    if endpoint is None:
        return {
            "encontrado": False,
            "path_consultado": path,
            "mensaje": f"No existe un endpoint que coincida con '{path}'.",
            "endpoints_disponibles": _endpoints_disponibles(data),
        }

    return {
        "encontrado": True,
        "path": endpoint["path"],
        "method": endpoint["method"],
        "ejemplo_payload": endpoint["request"]["body"]["example"],
    }


# ---------------------------------------------------------------------------
# 4. Interpretar un código de respuesta HTTP de un endpoint
# ---------------------------------------------------------------------------

def interpretar_codigo_respuesta(data: dict, path: str, status_code: int) -> dict:
    """
    Pregunta que resuelve: "¿Qué significa un 503 en el endpoint de
    motores?" — importante porque el significado de un mismo código
    puede variar según el endpoint (ej. 503 en 'motors' es falla de
    rotor, no un error genérico de servidor caído).
    """
    endpoint = _buscar_endpoint(data, path)
    if endpoint is None:
        return {
            "encontrado": False,
            "path_consultado": path,
            "mensaje": f"No existe un endpoint que coincida con '{path}'.",
            "endpoints_disponibles": _endpoints_disponibles(data),
        }

    for respuesta in endpoint["responses"]:
        if respuesta["status_code"] == status_code:
            return {
                "encontrado": True,
                "path": endpoint["path"],
                "status_code": status_code,
                "descripcion": respuesta["description"],
            }

    codigos_validos = [r["status_code"] for r in endpoint["responses"]]
    return {
        "encontrado": False,
        "path": endpoint["path"],
        "status_code_consultado": status_code,
        "mensaje": f"El endpoint '{endpoint['path']}' no documenta el código {status_code}.",
        "codigos_disponibles": codigos_validos,
    }


# ---------------------------------------------------------------------------
# 5. Buscar en qué endpoint(s) aparece un campo
# ---------------------------------------------------------------------------

def buscar_campo(data: dict, nombre_campo: str) -> dict:
    """
    Pregunta que resuelve: "¿Qué significa 'rpm'?" / "¿En qué endpoints
    se usa 'status_code'?" — búsqueda transversal, útil cuando el
    usuario no sabe (o no le importa) a qué endpoint pertenece un campo.
    """
    alias = _normalizar(nombre_campo)
    apariciones = []

    for endpoint in data["endpoints"]:
        for campo in _propiedades_aplanadas(endpoint):
            if _normalizar(campo["campo"]) == alias:
                apariciones.append(
                    {
                        "endpoint": endpoint["path"],
                        "tipo": campo["tipo"],
                        "descripcion": campo["descripcion"],
                        "requerido": campo["requerido"],
                    }
                )

    if not apariciones:
        return {
            "encontrado": False,
            "campo_consultado": nombre_campo,
            "mensaje": f"El campo '{nombre_campo}' no aparece en ningún endpoint documentado.",
        }

    return {
        "encontrado": True,
        "campo": nombre_campo,
        "cantidad_endpoints_donde_aparece": len(apariciones),
        "detalle": apariciones,
    }


# ---------------------------------------------------------------------------
# Prueba manual rápida
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    data = cargar_esquema_api()

    print("=== listar_endpoints() ===")
    print(json.dumps(listar_endpoints(data), indent=2, ensure_ascii=False))

    print("\n=== obtener_esquema_endpoint('motors') (coincidencia parcial) ===")
    print(json.dumps(obtener_esquema_endpoint(data, "motors"), indent=2, ensure_ascii=False))

    print("\n=== obtener_ejemplo_payload('environment') ===")
    print(json.dumps(obtener_ejemplo_payload(data, "environment"), indent=2, ensure_ascii=False))

    print("\n=== interpretar_codigo_respuesta('motors', 503) ===")
    print(json.dumps(interpretar_codigo_respuesta(data, "motors", 503), indent=2, ensure_ascii=False))

    print("\n=== interpretar_codigo_respuesta('environment', 503) (código NO documentado ahí) ===")
    print(json.dumps(interpretar_codigo_respuesta(data, "environment", 503), indent=2, ensure_ascii=False))

    print("\n=== buscar_campo('status_code') (aparece en ambos endpoints) ===")
    print(json.dumps(buscar_campo(data, "status_code"), indent=2, ensure_ascii=False))

    print("\n=== buscar_campo('rpm') (solo en motors) ===")
    print(json.dumps(buscar_campo(data, "rpm"), indent=2, ensure_ascii=False))

    print("\n=== endpoint inexistente (prueba de manejo de error) ===")
    print(json.dumps(obtener_esquema_endpoint(data, "vibracion"), indent=2, ensure_ascii=False))