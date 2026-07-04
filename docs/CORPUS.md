# Corpus Documental — Agente RAG Auvix

Todos los documentos son **ficticios**, generados con apoyo de IA con fines educativos (Challenge ONE — Alura Latam).

| Área | Formato | Documento | Usado en v1 (MVP) |
|---|---|---|---|
| Operacional | `.pdf` | Manual Técnico de Sintonización PID y Lazos de Control | ✅ Sí — fuente RAG |
| Financiero | `.csv` | Cruce Presupuestal de Hardware y OpEx | ✅ Sí — fuente Tool Pandas |
| Sistemas | `.xlsx` | Historial de Telemetría y Consumo Eléctrico de Nodos IoT | ⏳ Pendiente de definir rol (ver nota) |
| Integración | `.json` | Esquema de API y Payloads de Sensores | 🚫 Fase 2 |
| Telecomunicaciones | `.html` | Reporte de Auditoría de Redes y Protocolos de Enlace | 🚫 Fase 2 |
| Estratégico | `.md` | Arquitectura de Red y Despliegue de ML en OCI | 📄 Referencia interna (no se indexa como RAG) |

## Nota sobre el archivo de Telemetría (`Datos_Nodos_Julio_2026.xlsx`)

Agregado al proyecto pero pendiente de confirmar su rol funcional en el Tool de Pandas:
- ¿Reemplaza al CSV financiero?
- ¿Es una segunda fuente y el router elige entre ambas?
- ¿Solo queda documentado en el corpus sin uso activo en v1?

Actualizar esta tabla una vez definido.
