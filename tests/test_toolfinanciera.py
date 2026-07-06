import os
import sys
import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

from src.tools.financiero import (
    total_por_departamento,
    total_por_categoria,
    transacciones_por_estado,
    resumen_general,
    transaccion_mas_alta,
    transaccion_mas_baja
)

def crear_dataframe_prueba() -> pd.DataFrame:
    datos = {
        "ID_Transaccion": ["TX01", "TX02", "TX03", "TX04"],
        "Fecha": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
        "Departamento": ["Infraestructura", "Infraestructura", "Ventas", "Marketing"],
        "Categoria": ["Hardware", "OpEx", "Hardware", "Software"],
        "Descripcion_Articulo": ["Servidor RACK", "Mantenimiento", "Laptop", "Licencia CRM"],
        "Monto_USD": [5000.0, 200.0, 1500.0, 300.0],
        "Estado_Aprobacion": ["Aprobado", "Rechazado", "Pendiente", "Aprobado"]
    }
    return pd.DataFrame(datos)

def ejecutar_pruebas():
    print("INICIANDO PRUEBAS DE HERRAMIENTA FINANCIERA (PANDAS)...\n")
    df = crear_dataframe_prueba()

    print("--- PRUEBA 1: Total por Departamento (Infraestructura) ---")
    resultado = total_por_departamento(df, "infraestructura") # Probamos en minúscula
    if resultado["encontrado"] and resultado["total_usd"] == 5200.0:
        print("Éxito: Suma correcta (5000 + 200) y normalización funcionando.")
    else:
        print(f"Error en cálculo: {resultado}")

    print("\n--- PRUEBA 2: Departamento Inexistente (Manejo de Errores) ---")
    resultado = total_por_departamento(df, "Recursos Humanos")
    if not resultado["encontrado"]:
        print("Éxito: El sistema detectó correctamente que el departamento no existe.")
        print(f"   Mensaje del sistema: {resultado['mensaje']}")
    else:
        print(f"Error: Aprobó un departamento fantasma.")

    print("\n--- PRUEBA 3: Total por Categoría (Hardware) ---")
    resultado = total_por_categoria(df, "Hardware")
    if resultado["total_usd"] == 6500.0: # 5000 + 1500
        print(f"Éxito: Suma de Hardware correcta (${resultado['total_usd']}).")
    else:
        print(f"Error en cálculo: {resultado}")

    print("\n--- PRUEBA 4: Transacciones por Estado (Rechazado) ---")
    resultado = transacciones_por_estado(df, "RECHAZADO")
    if resultado["cantidad_transacciones"] == 1 and resultado["total_usd"] == 200.0:
        print("Éxito: Filtrado por estado correcto.")
    else:
        print(f"Error en filtrado: {resultado}")

    print("\n--- PRUEBA 5: Transacciones Extremas (Max / Min) ---")
    alta = transaccion_mas_alta(df)
    baja = transaccion_mas_baja(df)
    if alta["transaccion"]["monto_usd"] == 5000.0 and baja["transaccion"]["monto_usd"] == 200.0:
        print(f"Éxito: Detectó la más alta (${alta['transaccion']['monto_usd']}) y la más baja (${baja['transaccion']['monto_usd']}).")
    else:
        print("Error detectando extremos.")

    print("\n--- PRUEBA 6: Resumen General (Formato Compacto) ---")
    resumen = resumen_general(df)
    if resumen["total_usd_global"] == 7000.0 and len(resumen["por_departamento"]) == 3:
        print("Éxito: El resumen global se generó con la estructura correcta.")
    else:
        print("Error en el resumen general.")

    print("\nTodas las pruebas de lógica de datos finalizadas.")

if __name__ == "__main__":
    ejecutar_pruebas()