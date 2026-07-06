import os
import sys
import json

# 1. Configurar el path para incluir el directorio 'src'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

# 2. Importar funciones y el cargador de datos reales
from src.tools.telemetria import (
    cargar_datos_telemetria,
    historico_por_nodo,
    nodos_en_alerta,
    promedio_por_nodo,
    resumen_general,
    lectura_mas_alta,
    lectura_mas_baja
)

def ejecutar_pruebas_reales():
    print("INICIANDO PRUEBAS DE INTEGRACIÓN: TELEMETRÍA IOT")
    print("-" * 60)

    try:
        df = cargar_datos_telemetria()
        print(f"Archivo cargado exitosamente. Total de registros en memoria: {len(df)}")
    except Exception as e:
        print(f"Fallo crítico al cargar el archivo XLSX: {e}")
        return

    print("\n[PRUEBA 1] Histórico por Nodo (NODO-L4-03)")
    res_historico = historico_por_nodo(df, "NODO-L4-03")
    # Se trunca la salida en consola si es muy larga para mantener legibilidad
    salida_historico = json.dumps(res_historico, indent=2, ensure_ascii=False)
    print(salida_historico[:500] + "\n... [Salida truncada para consola]")

    print("\n[PRUEBA 2] Nodos en Alerta")
    res_alerta = nodos_en_alerta(df)
    print(json.dumps(res_alerta, indent=2, ensure_ascii=False))

    print("\n[PRUEBA 3] Promedio por Nodo (NODO-L4-01)")
    res_promedio = promedio_por_nodo(df, "NODO-L4-01")
    print(json.dumps(res_promedio, indent=2, ensure_ascii=False))

    print("\n[PRUEBA 4] Resumen General de la Red")
    res_resumen = resumen_general(df)
    print(json.dumps(res_resumen, indent=2, ensure_ascii=False))

    print("\n[PRUEBA 5] Extremos Operativos por Métrica")
    res_alta = lectura_mas_alta(df, "temperatura")
    res_baja = lectura_mas_baja(df, "latencia")
    print("Lectura más alta (Temperatura):")
    print(json.dumps(res_alta, indent=2, ensure_ascii=False))
    print("Lectura más baja (Latencia):")
    print(json.dumps(res_baja, indent=2, ensure_ascii=False))

    print("\n[PRUEBA 6] Validación de Manejo de Excepciones")
    res_error_nodo = historico_por_nodo(df, "NODO-L4-99")
    res_error_metrica = lectura_mas_alta(df, "presion_atmosferica")
    print("Respuesta ante nodo inexistente:")
    print(json.dumps(res_error_nodo, indent=2, ensure_ascii=False))
    print("Respuesta ante métrica no soportada:")
    print(json.dumps(res_error_metrica, indent=2, ensure_ascii=False))

    print("-" * 60)
    print("Ejecución de pruebas finalizada.")

if __name__ == "__main__":
    ejecutar_pruebas_reales()