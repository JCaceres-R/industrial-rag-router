import os
import sys

# 1. Configurar el path para que Python encuentre la carpeta 'src'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

# 2. Importar tus módulos
from src.rag.chunking import chunk_text, chunk_document
from src.ingestion.loaders import load_pdf

# 3. Ruta al manual de sintonización PID de Auvix
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
FILE_PDF = os.path.join(DATA_DIR, "Manual Técnico PID y Lazos de Control_Auvix.pdf")

def ejecutar_pruebas():
    print("Iniciando pruebas de Chunking de Texto (Auvix MVP)...\n")

    # --- PRUEBA 1: Validación de seguridad (Rechazo de Tabular) ---
    print("-" * 50)
    print("Prueba 1: Probando barrera de seguridad de tipos de archivo...")
    try:
        chunk_document(tipo_contenido="tabular", contenido="Columna1,Columna2\n1,2")
        print("Falla: El sistema permitió trocear un tabular. Revisa la lógica.")
    except ValueError as e:
        print(f"Éxito! El sistema bloqueó el tabular correctamente.")
        print(f"Mensaje de error capturado: {e}\n")

    # --- PRUEBA 2: Troceado Real del Manual PID ---
    print("-" * 50)
    print("Prueba 2: Probando chunking real con el PDF de Auvix...")
    try:
        # Primero cargamos el texto crudo usando tu loader
        texto_crudo = load_pdf(FILE_PDF)
        print(f"Texto original cargado. Longitud total: {len(texto_crudo)} caracteres.")

        # Ahora lo pasamos por el chunker (usamos tamaños pequeños para forzar cortes)
        TAMANO_CHUNK = 800
        SOLAPAMIENTO = 150
        chunks = chunk_document("texto", texto_crudo, chunk_size=TAMANO_CHUNK, overlap=SOLAPAMIENTO)
        
        print(f"Éxito! El documento se dividió en {len(chunks)} fragmentos (chunks).")
        
        # Mostramos los dos primeros chunks para validar el solapamiento visualmente
        if len(chunks) >= 2:
            print("\n---CHUNK 0 (Primeros y últimos caracteres) ---")
            print(f"INICIO: {chunks[0][:100]}...")
            print(f"FIN: ...{chunks[0][-100:]}")
            print(f"Tamaño: {len(chunks[0])} caracteres")

            print("\n---CHUNK 1 (Deberías ver solapamiento con el FIN del Chunk 0) ---")
            print(f"INICIO: {chunks[1][:150]}...")
            print(f"Tamaño: {len(chunks[1])} caracteres")
            
    except Exception as e:
        print(f"Error durante el troceado del PDF: {e}\n")

    print("-" * 50)
    print("Pruebas finalizadas.")

if __name__ == "__main__":
    ejecutar_pruebas()