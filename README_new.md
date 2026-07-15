# Industrial RAG Router

Aplicación de asistencia inteligente para entornos industriales basada en un sistema RAG y un grafo de routing con LangGraph. El proyecto combina:

- búsqueda semántica sobre documentación técnica,
- herramientas determinísticas para análisis financiero y telemetría,
- un router multi-rama que dirige las consultas al módulo correcto,
- una interfaz web construida con Streamlit.

El proyecto está pensado para ejecutarse de forma local o en contenedores, y para desplegarse en OCI Always Free sobre una VM ARM.

---

## Características principales

- Interfaz Streamlit con experiencia visual orientada a operaciones industriales.
- Router basado en LangGraph para clasificar consultas entre:
  - documentación técnica (RAG),
  - financiero,
  - telemetría,
  - esquema API.
- Recuperación semántica con embeddings y FAISS.
- Análisis tabular y financiero con pandas.
- Soporte para despliegue con Docker y Docker Compose.
- Preparado para ejecución en OCI VM.Standard.A1.Flex.

---

## Estructura del proyecto

```text
industrial-rag-router/
├── app.py                  # Punto de entrada de Streamlit
├── Dockerfile              # Imagen Docker para la aplicación
├── docker-compose.yml      # Orquestación local con Docker Compose
├── requirements.txt        # Dependencias de Python
├── .env.example            # Variables de entorno de ejemplo
├── data/                   # Datos y documentos fuente
├── docs/                   # Documentación técnica
├── faiss_index/            # Índice FAISS y chunks
├── src/                    # Código fuente del proyecto
│   ├── graph/              # Router, nodos y estado del grafo
│   ├── ingestion/          # Carga de documentos y loaders
│   ├── rag/                # Chunking, retriever y vectorstore
│   ├── tools/              # Herramientas financieras, telemétricas y de esquema
│   └── ui/                 # Componentes de interfaz
└── tests/                  # Pruebas unitarias
```

---

## Requisitos

- Python 3.10 o superior
- Docker y Docker Compose (opcional, para despliegue en contenedores)
- Cuenta de Groq con API key

---

## Variables de entorno

Copia el archivo [.env.example](.env.example) a `.env` y completa los valores:

```bash
copy .env.example .env
```

Variables esperadas:

```env
GROQ_API_KEY=tu_api_key
GROQ_MODEL=openai/gpt-oss-120b
VECTOR_STORE_PATH=./data/vector_store
STREAMLIT_PORT=8501
```

---

## Ejecución local

### Opción 1: Python

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

### Opción 2: Docker

```bash
docker compose up --build
```

La aplicación quedará disponible en:

```text
http://localhost:8501
```

---

## Despliegue en OCI Always Free

Este proyecto está preparado para desplegarse en una VM ARM como `VM.Standard.A1.Flex`.

### Recomendación de infraestructura

- Shape: `VM.Standard.A1.Flex`
- CPU/RAM: 2 OCPUs / 12 GB RAM
- Sistema operativo: Ubuntu 24.04 ARM64 o Oracle Linux 8/9
- Puerto abierto: `8501`

### Pasos básicos en la VM

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Luego:

```bash
git clone <tu-repositorio>
cd industrial-rag-router
cp .env.example .env
nano .env
docker compose up --build -d
```

Para verificar:

```bash
curl http://localhost:8501
```

> En OCI debes abrir el puerto 8501 en la Security List o NSG para permitir acceso público.

---

## Pruebas

Ejecuta las pruebas con:

```bash
pytest -q
```

---

## Notas importantes

- El proyecto usa datos locales y un índice FAISS, por lo que la carpeta `data/` y `faiss_index/` deben estar presentes en el entorno de ejecución.
- Para producción, conviene proteger las credenciales con variables de entorno del proveedor cloud o un gestor de secretos.
- Si deseas exponer la app con HTTPS, puedes colocar un proxy inverso como Nginx o Caddy delante de Streamlit.

---

## Licencia

Proyecto educativo y de portafolio para demostrar un flujo completo de IA empresarial con RAG, herramientas, routing y despliegue en nube.
