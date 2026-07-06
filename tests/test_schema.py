import os
import sys
import json

# 1. Configurar el path para incluir el directorio 'src'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

# 2. Importar funciones y el cargador del esquema real
from src.tools.api_schema import (
    cargar_esquema_api,
    listar_endpoints,
    obtener_esquema_endpoint,
    obtener_ejemplo_payload,
    interpretar_codigo_respuesta,
    buscar_campo
)

def ejecutar_pruebas_esquema_api():
    print("INICIANDO PRUEBAS DE INTEGRACIÓN: ESQUEMA DE API IOT")
    print("-" * 60)

    try:
        data = cargar_esquema_api()
        nombre_api = data.get("api_name", "Desconocida")
        version = data.get("version", "N/A")
        print(f"Archivo JSON cargado exitosamente. API detectada: {nombre_api} (v{version})")
    except Exception as e:
        print(f"Fallo crítico al cargar el archivo JSON: {e}")
        return

    print("\n[PRUEBA 1] Listar Endpoints Disponibles")
    res_endpoints = listar_endpoints(data)
    print(json.dumps(res_endpoints, indent=2, ensure_ascii=False))

    print("\n[PRUEBA 2] Esquema Aplanado de Endpoint (Coincidencia parcial: 'motors')")
    res_esquema = obtener_esquema_endpoint(data, "motors")
    # Truncamos la salida en consola para no saturar si hay muchos campos
    salida_esquema = json.dumps(res_esquema, indent=2, ensure_ascii=False)
    print(salida_esquema[:600] + "\n... [Salida de campos truncada para consola]")

    print("\n[PRUEBA 3] Extracción de Payload de Ejemplo ('environment')")
    res_payload = obtener_ejemplo_payload(data, "environment")
    print(json.dumps(res_payload, indent=2, ensure_ascii=False))

    print("\n[PRUEBA 4] Interpretación de Códigos HTTP (Endpoint 'motors', Código 503)")
    res_codigo = interpretar_codigo_respuesta(data, "motors", 503)
    print(json.dumps(res_codigo, indent=2, ensure_ascii=False))

    print("\n[PRUEBA 5] Búsqueda Transversal de Campos")
    print("Buscando campo 'status_code' (esperado en múltiples endpoints):")
    res_campo_multiple = buscar_campo(data, "status_code")
    print(json.dumps(res_campo_multiple, indent=2, ensure_ascii=False))
    
    print("\nBuscando campo 'rpm' (esperado solo en motors):")
    res_campo_unico = buscar_campo(data, "rpm")
    print(json.dumps(res_campo_unico, indent=2, ensure_ascii=False))

    print("\n[PRUEBA 6] Validación de Manejo de Excepciones y Datos Inexistentes")
    res_error_endpoint = obtener_esquema_endpoint(data, "vibracion")
    res_error_codigo = interpretar_codigo_respuesta(data, "environment", 503)
    print("Respuesta ante endpoint no documentado ('vibracion'):")
    print(json.dumps(res_error_endpoint, indent=2, ensure_ascii=False))
    print("Respuesta ante código HTTP no documentado en ese endpoint específico:")
    print(json.dumps(res_error_codigo, indent=2, ensure_ascii=False))

    print("-" * 60)
    print("Ejecución de pruebas finalizada.")

if __name__ == "__main__":
    ejecutar_pruebas_esquema_api()