# Arquitectura Técnica — Agente RAG Auvix

Referencia interna alineada con `ProyectoOracle__AI_BUILDER.pdf` (documento fuente del challenge).

## 1. Flujo general

```
Usuario (Streamlit)
      │
      ▼
┌─────────────────┐
│  Router (LangGraph) │  ← clasifica intención de la consulta
└─────────────────┘
      │
      ├── Consulta teórica ──────► Nodo RAG (vector store) ──► Manual PID (.pdf)
      │
      └── Consulta analítica ────► Nodo Tool (Pandas) ──────► Datos financieros (.csv)
      │
      ▼
  Memoria de sesión (checkpointer) ── persiste estado entre turnos
      │
      ▼
  Respuesta al usuario
```

## 2. Componentes

### 2.1 Router (`src/graph/`)
Nodo de entrada del `StateGraph`. Clasifica la consulta del usuario en una de dos ramas:
- **Rama teórica** → se deriva al nodo RAG.
- **Rama analítica** → se deriva al nodo Tool de Pandas.

Debe implementarse evitando llamadas redundantes al LLM para la clasificación, priorizando latencia baja y bajo consumo de tokens.

### 2.2 Nodo RAG (`src/rag/`)
Pipeline de ingesta del `Manual_Técnico_PID_y_Lazos_de_Control_Auvix.pdf`:
1. Extracción de texto del PDF.
2. Chunking (tamaño ajustado al límite de 8.000 TPM de Groq).
3. Generación de embeddings y almacenamiento local (FAISS/ChromaDB).
4. Recuperación de los *top-k* chunks relevantes por consulta — nunca se inyecta el documento completo al prompt.

### 2.3 Tool de análisis numérico (`src/tools/`)
Envuelve la lógica de Pandas sobre `DatosFinancieros_Auvix.csv`:
- Filtra y agrega valores (ej. cruce de gastos OpEx) **dentro del proceso Python**.
- Devuelve al LLM únicamente el resultado calculado (no el DataFrame completo), para no saturar la ventana de contexto ni el límite TPM.

### 2.4 Memoria de sesión
Uso del *checkpointer* nativo de LangGraph para persistir el historial de interacciones y permitir resolución de pronombres/referencias cruzadas en preguntas secuenciales.

### 2.5 Despliegue
- Instancia OCI Ampere A1 (Always Free), ver guía detallada de red y despliegue del área de Arquitectura Cloud.
- Exposición vía Streamlit en el puerto `8501`.
- Ejecución persistente con `tmux` o `nohup` (ver sección de infraestructura en el README).

## 3. Gestión de límites de la API Groq

| Proveedor | Modelo | Límite RPM | Límite TPM |
|---|---|---|---|
| OpenAI (vía Groq) | gpt-oss-120b | 30 | 8.000 |
| Qwen (vía Groq) | qwen3.6-27b | 30 | 8.000 |

**Estrategia de mitigación:** el `StateGraph` debe controlar explícitamente cuánto contexto se extrae del vector store o de los DataFrames antes de inyectarlo en el prompt final.

## 4. Fuera de alcance en v1

- Ingesta de `IntegracionDeSistemas_Auvix.json` (esquema API de sensores IoT).
- Ingesta de `auditoria_redes.html` (reporte de auditoría de redes).

Ambos quedan definidos como **Fase 2** del roadmap; no se implementan en el Vertical Slice actual.
