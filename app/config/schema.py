from sqlalchemy import text


def create_search_indexes(connection) -> None:
    """Cria índices locais usados pela recuperação híbrida."""

    connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw "
            "ON chunks USING hnsw (embedding vector_cosine_ops)"
        )
    )
    connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv "
            "ON chunks USING gin (to_tsvector('portuguese', content))"
        )
    )
    connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_chunks_document_position "
            "ON chunks (document_id, chunk_index)"
        )
    )
    connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_chunks_type_document "
            "ON chunks (chunk_type, document_id)"
        )
    )
