import os
import sys

# 1. Configurar el path para que Python encuentre la carpeta 'src'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

# 2. Importar tus loaders
from src.ingestion.loaders import load_pdf, load_html, load_tabular, load_json

# 3. Definir las rutas exactas de los archivos del corpus
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

FILE_PDF = os.path.join(DATA_DIR, "Manual Técnico PID y Lazos de Control_Auvix.pdf")
FILE_HTML = os.path.join(DATA_DIR, "auditoria_redes.html")
FILE_CSV = os.path.join(DATA_DIR, "DatosFinancieros_Auvix.csv")
FILE_JSON = os.path.join(DATA_DIR, "IntegracionDeSistemas_Auvix.json")

def ejecutar_pruebas():
    print("🚀 Iniciando pruebas de Ingestión de Datos (Auvix MVP)...\n")

    # --- PRUEBA 1: PDF ---
    print("-" * 50)
    try:
        print("📄 Probando PDF Loader...")
        texto_pdf = load_pdf(FILE_PDF)
        print(f"✅ Éxito! Se extrajeron {len(texto_pdf)} caracteres.")
        print(f"Muestra inicial:\n{texto_pdf[:150]}...\n")
    except Exception as e:
        print(f"❌ Error leyendo PDF: {e}\n")

    # --- PRUEBA 2: HTML ---
    print("-" * 50)
    try:
        print("🌐 Probando HTML Loader...")
        texto_html = load_html(FILE_HTML)
        print(f"✅ Éxito! Se extrajeron {len(texto_html)} caracteres (limpios de etiquetas).")
        print(f"Muestra inicial:\n{texto_html[:150]}...\n")
    except Exception as e:
        print(f"❌ Error leyendo HTML: {e}\n")

    # --- PRUEBA 3: TABULAR (CSV) ---
    print("-" * 50)
    try:
        print("📊 Probando Tabular Loader (CSV/Pandas)...")
        df_csv = load_tabular(FILE_CSV)
        print(f"✅ Éxito! DataFrame cargado con {df_csv.shape[0]} filas y {df_csv.shape[1]} columnas.")
        print("Primeras 3 filas:")
        print(df_csv.head(3))
        print("\n")
    except Exception as e:
        print(f"❌ Error leyendo Tabular: {e}\n")

    # --- PRUEBA 4: JSON ---
    print("-" * 50)
    try:
        print("🔧 Probando JSON Loader...")
        datos_json = load_json(FILE_JSON)
        nombre_api = datos_json.get("api_name", "Desconocido")
        print(f"✅ Éxito! Archivo JSON parseado a diccionario.")
        print(f"Nombre de la API detectado: {nombre_api}")
        print(f"Cantidad de endpoints: {len(datos_json.get('endpoints', []))}\n")
    except Exception as e:
        print(f"❌ Error leyendo JSON: {e}\n")

    print("-" * 50)
    print("🏁 Pruebas finalizadas.")

if __name__ == "__main__":
    ejecutar_pruebas()