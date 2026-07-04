"""
Pipeline RAG sobre el Manual Técnico PID (.pdf).

Contendrá:
- ingest.py   -> extracción de texto y chunking del PDF
- vectorstore.py -> creación/carga de embeddings (FAISS/ChromaDB)
- retriever.py   -> recuperación de chunks relevantes por consulta
"""
