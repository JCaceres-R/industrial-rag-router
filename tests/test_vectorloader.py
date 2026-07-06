import os
import sys

# 1. Configurar el path para que Python encuentre la carpeta 'src'
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

# 2. Importar tus 3 módulos creados
from src.ingestion.loaders import load_pdf
from src.rag.chunking import chunk_document
from src.rag.vectorstore import construir_vectorstore, cargar_vectorstore, cargar_modelo_embeddings

# 3. Definir rutas de datos
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
FILE_PDF = os.path.join(DATA_DIR, "Manual Técnico PID y Lazos de Control_Auvix.pdf")
CARPES_DB = os.path.join(BASE_DIR, "faiss_index")

def ejecutar_test_completo():
    print("INICIANDO INTEGRACIÓN PROCESO VECTORIAL (Auvix MVP)...\n")

    # --- PASO 1: Ingestión y Chunking ---
    print("Cargando y troceando el manual PDF...")
    texto_crudo = load_pdf(FILE_PDF)
    chunks = chunk_document("texto", texto_crudo, chunk_size=700, overlap=100)
    print(f"Documento dividido en {len(chunks)} fragmentos.")

    # --- PASO 2: Carga de Modelo y Creación de Vectores ---
    print("\nInicializando modelo de embeddings y generando base FAISS...")
    modelo = cargar_modelo_embeddings()
    
    # Esto creará 'index.faiss' y 'chunks.json' en la carpeta faiss_index/
    construir_vectorstore(chunks, CARPES_DB, modelo)
    print("Base de datos vectorial indexada y guardada en disco.")

    # --- PASO 3: Simular una consulta del usuario (Búsqueda Semántica pura) ---
    print("\n Simulando consulta de usuario...")
    
    # Cargamos el mapa vectorial recién creado para demostrar que lee desde disco
    indice_faiss, textos_guardados = cargar_vectorstore(CARPES_DB)
    
    # Pregunta técnica sobre sintonización PID (Ziegler-Nichols)
    pregunta_usuario = "¿Cómo se calculan los parámetros usando el método de Ziegler-Nichols?"
    print(f" Pregunta formulada: '{pregunta_usuario}'")
    
    # Convertimos la pregunta en coordenadas (vector) usando el mismo modelo
    vector_pregunta = modelo.encode([pregunta_usuario]).astype("float32")
    
    # FAISS busca los K elementos más cercanos (vamos a pedir los 2 mejores)
    K_RESULTADOS = 2
    distancias, indices_ganadores = indice_faiss.search(vector_pregunta, K_RESULTADOS)
    
    print("\n --- RESULTADOS DE LA BÚSQUEDA EN FAISS ---")
    for i in range(K_RESULTADOS):
        posicion_chunk = indices_ganadores[0][i]
        distancia_matematica = distancias[0][i]
        texto_recuperado = textos_guardados[posicion_chunk]
        
        print(f"\n Resultado #{i+1} (Chunk de texto #{posicion_chunk})")
        print(f" Distancia Euclidiana (Menor = Más similar): {distancia_matematica:.4f}")
        print(f" Fragmento recuperado:\n{texto_recuperado[:300]}...")
        print("-" * 40)

if __name__ == "__main__":
    ejecutar_test_completo()