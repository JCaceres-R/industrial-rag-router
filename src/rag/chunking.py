
from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(texto: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """
    Corta un texto largo en fragmentos pequeños con solapamiento entre ellos.

    Parámetros:
        texto: el texto completo del documento (ej. lo que devuelve load_pdf()).
        chunk_size: tamaño máximo de cada fragmento, en caracteres.
        overlap: cuántos caracteres se repiten entre un chunk y el siguiente,
                 para no perder contexto justo en el borde del corte.

    Devuelve:
        Una lista de strings. Cada elemento es un chunk listo para convertirse
        en un embedding en vectorstore.py.

    Nota sobre "Recursive": este splitter no corta a la fuerza en cualquier
    caracter. Primero intenta cortar por párrafos (\\n\\n), si el fragmento
    sigue siendo muy largo intenta por oraciones, y solo como último recurso
    corta por caracter suelto. Esto evita partir una oración a la mitad.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", ". ", " ", ""],  # orden de preferencia de corte
    )

    return splitter.split_text(texto)


def chunk_document(tipo_contenido: str, contenido, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    """
    Punto de entrada pensado para conectar directamente con registry.load_document().

    Solo trocea si el documento es de tipo "texto" (PDF, HTML).
    Los documentos "tabular" o "json" no pasan por aquí — esos van
    directo a tools/tabular.py o tools/api_schema.py sin chunking,
    porque no son prosa y no se vectorizan.
    """
    if tipo_contenido != "texto":
        raise ValueError(
            f"chunk_document() solo procesa contenido tipo 'texto'. "
            f"Recibido: '{tipo_contenido}'. Los tipos 'tabular' y 'json' "
            f"no se trocean — van directo a un Tool."
        )

    return chunk_text(contenido, chunk_size=chunk_size, overlap=overlap)