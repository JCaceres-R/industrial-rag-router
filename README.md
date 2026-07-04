# Agente de IA Corporativo Auvix (Sistema RAG)

Agente de Inteligencia Artificial corporativo basado en arquitectura **RAG (Retrieval-Augmented Generation)** para Auvix, empresa ficticia de automatización industrial, control de procesos y Edge AI.

El sistema enruta consultas de usuario entre búsqueda semántica (documentación técnica) y análisis determinístico (datos tabulares), desplegado en Oracle Cloud Infrastructure (OCI) bajo la capa Always Free, operando dentro de los límites estrictos de tokens de la API gratuita de Groq.

> Proyecto desarrollado como Challenge del programa Oracle Next Education (ONE) — Alura Latam. Todos los documentos del corpus (PDF, CSV, JSON, HTML, MD) contienen datos ficticios generados con apoyo de IA.

---

## 1. Alcance del MVP (Vertical Slice)

La v1 se enfoca en un **Vertical Slice** de 5 habilidades arquitectónicas, sin funcionalidades periféricas:

| # | Habilidad | Descripción |
|---|---|---|
| 1 | **RAG sobre PDF Técnico** | Extracción de conocimiento teórico (métodos de sintonización PID) desde el manual operativo. |
| 2 | **Tool Calling Determinístico** | Cálculos financieros exactos sobre hojas de cálculo (cruce presupuestal OpEx) vía Pandas. |
| 3 | **Router con LangGraph** | Nodo de decisión semántica que enruta la consulta hacia el motor vectorial o el motor tabular. |
| 4 | **Memoria de Sesión** | Checkpointer de LangGraph para mantener estado conversacional en consultas encadenadas. |
| 5 | **Despliegue en Nube** | Interfaz pública en Streamlit sobre instancia OCI Ampere A1 (Always Free). |

**Fuera de alcance en v1 (Fase 2):** ingesta de `IntegracionDeSistemas_Auvix.json` y `auditoria_redes.html`. Se documentan como roadmap futuro, pero no se implementan en el MVP.

---

## 2. Stack Tecnológico

- **Orquestación:** LangGraph (StateGraph) + LangChain
- **LLM:** Groq API (`openai/gpt-oss-120b` o `qwen/qwen3.6-27b`) — límite 30 RPM / 8.000 TPM
- **Vector Store:** FAISS o ChromaDB (embeddings locales)
- **Datos estructurados:** Pandas + openpyxl
- **Interfaz:** Streamlit
- **Infraestructura:** OCI Compute Ampere A1 (ARM), 2 OCPUs / 12 GB RAM, Always Free

---

## 3. Estructura del repositorio

```
auvix-agente-ia/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── docs/
│   ├── ARQUITECTURA.md        # Diseño técnico detallado del grafo y componentes
│   └── CORPUS.md              # Matriz de documentos fuente del sistema RAG
├── data/
│   └── raw/                   # PDF, CSV/XLSX fuente (no versionados, ver .gitignore)
├── src/
│   ├── app.py                 # Punto de entrada Streamlit
│   ├── graph/                 # Definición del StateGraph (router, nodos, aristas)
│   ├── rag/                   # Pipeline de ingesta y consulta vectorial (PDF)
│   ├── tools/                 # Tool de análisis numérico (Pandas sobre CSV/XLSX)
│   └── ui/                    # Componentes de interfaz Streamlit
└── tests/                     # Pruebas unitarias por componente
```

---

## 4. Estado actual (v1)

- [x] Estructura de repositorio y documentación base
- [ ] Entorno virtual + `requirements.txt` validado
- [ ] Pipeline RAG sobre manual PID (chunking + embeddings)
- [ ] Tool de Pandas sobre datos financieros
- [ ] Router LangGraph (RAG vs. Tool)
- [ ] Memoria de sesión (checkpointer)
- [ ] Despliegue en OCI + Streamlit público

---

## 5. Instalación local (referencia rápida)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # completar GROQ_API_KEY
streamlit run src/app.py
```

## 6. Licencia

Proyecto educativo/portafolio. Uso libre con fines de aprendizaje.
