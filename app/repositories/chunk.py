import hashlib
import re
from dataclasses import dataclass, replace
from unicodedata import normalize
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.chunk import Chunk
from app.repositories.base import BaseRepository


@dataclass(frozen=True)
class RetrievedChunk:
    """Chunk recuperado junto com informações de ranking."""

    chunk: Chunk
    score: float
    vector_distance: float | None = None
    lexical_score: float | None = None
    term_overlap: float = 0.0
    subquery: str | None = None

    @property
    def content(self) -> str:
        """Atalho para manter o uso do conteúdo simples."""

        return self.chunk.content

    @property
    def document_filename(self) -> str:
        """Nome do documento de origem."""

        return self.chunk.document.filename

    @property
    def chunk_index(self) -> int:
        """Posição do chunk dentro do documento."""

        return self.chunk.chunk_index

    @property
    def page(self) -> int | None:
        """Página de origem, quando disponível."""

        return getattr(self.chunk, "page", None)

    @property
    def section(self) -> str | None:
        """Seção de origem, quando disponível."""

        return getattr(self.chunk, "section", None)

    @property
    def content_hash(self) -> str:
        """Hash estável do conteúdo para deduplicação."""

        content_hash = getattr(self.chunk, "content_hash", None)

        return content_hash or hashlib.sha256(
            self.content.encode("utf-8")
        ).hexdigest()

    @property
    def chunk_type(self) -> str:
        """Tipo do chunk usado na recuperação."""

        return getattr(self.chunk, "chunk_type", "content")


@dataclass(frozen=True)
class ChunkCreateData:  # pylint: disable=too-many-instance-attributes
    """Dados necessários para persistir um chunk."""

    document_id: UUID
    content: str
    embedding: list[float]
    chunk_index: int = 0
    page: int | None = None
    section: str | None = None
    start_char: int | None = None
    end_char: int | None = None
    content_hash: str | None = None
    chunk_type: str = "content"


@dataclass(frozen=True)
class HybridSearchWeights:
    """Pesos usados no rerank híbrido."""

    vector: float = 0.65
    lexical: float = 0.25
    term_overlap: float = 0.10


@dataclass(frozen=True)
class HybridSearchOptions:
    """Opções da busca híbrida."""

    limit: int = 5
    vector_limit: int | None = None
    lexical_limit: int | None = None
    max_distance: float | None = None
    weights: HybridSearchWeights = HybridSearchWeights()
    chunk_type: str | None = None


class ChunkRepository(BaseRepository):
    """Repository responsável pelos chunks."""

    def __init__(self, session: Session):
        super().__init__(session)

    def create(
        self,
        data: ChunkCreateData | None = None,
        **overrides,
    ) -> Chunk:
        """Cria um novo chunk."""

        chunk_data = self._chunk_create_data(data, overrides)
        content_hash = chunk_data.content_hash or hashlib.sha256(
            chunk_data.content.encode("utf-8")
        ).hexdigest()
        chunk = Chunk(
            document_id=chunk_data.document_id,
            content=chunk_data.content,
            embedding=chunk_data.embedding,
            chunk_index=chunk_data.chunk_index,
            char_count=len(chunk_data.content),
            chunk_type=chunk_data.chunk_type,
            page=chunk_data.page,
            section=chunk_data.section,
            start_char=chunk_data.start_char,
            end_char=chunk_data.end_char,
            content_hash=content_hash,
        )

        self.add(chunk)

        return chunk

    def _chunk_create_data(
        self,
        data: ChunkCreateData | None,
        overrides: dict[str, object],
    ) -> ChunkCreateData:
        """Normaliza entrada nova e kwargs legados para criação."""

        if data is None:
            return ChunkCreateData(**overrides)

        if overrides:
            return replace(data, **overrides)

        return data

    def get_by_id(self, chunk_id: UUID) -> Chunk | None:
        """Busca um chunk pelo ID."""

        statement = select(Chunk).where(Chunk.id == chunk_id)

        return self.scalar(statement)

    def get_by_document(self, document_id: UUID) -> list[Chunk]:
        """Retorna todos os chunks de um documento."""

        statement = (
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
        )

        return list(self.scalars(statement))

    def count(self) -> int:
        """Retorna a quantidade de chunks."""

        statement = select(func.count()).select_from(Chunk)

        return self.scalar(statement)

    def search_similar(
        self,
        embedding: list[float],
        limit: int = 5,
        max_distance: float | None = None,
        chunk_type: str | None = None,
    ) -> list[RetrievedChunk]:
        """Busca chunks mais próximos do embedding informado."""

        distance_expression = Chunk.embedding.cosine_distance(embedding)
        distance = distance_expression.label("score")
        statement = (
            select(Chunk, distance)
            .options(selectinload(Chunk.document))
            .order_by(distance_expression)
            .limit(limit)
        )

        if chunk_type is not None:
            statement = statement.where(Chunk.chunk_type == chunk_type)

        rows = self.session.execute(statement).all()
        results = [
            RetrievedChunk(
                chunk=chunk,
                score=float(score),
                vector_distance=float(score),
            )
            for chunk, score in rows
            if max_distance is None or float(score) <= max_distance
        ]

        return results

    def search_hybrid(
        self,
        query: str,
        embedding: list[float],
        options: HybridSearchOptions | None = None,
        **overrides,
    ) -> list[RetrievedChunk]:
        """Busca híbrida: pgvector + full text search + rerank local."""

        search_options = self._hybrid_search_options(options, overrides)
        vector_limit = search_options.vector_limit or search_options.limit
        lexical_limit = search_options.lexical_limit or search_options.limit
        vector_rows = self._search_vector_rows(
            embedding=embedding,
            limit=vector_limit,
            max_distance=search_options.max_distance,
            chunk_type=search_options.chunk_type,
        )
        lexical_rows = self._search_lexical_rows(
            query=query,
            limit=lexical_limit,
            chunk_type=search_options.chunk_type,
        )
        merged = self._merge_hybrid_rows(
            query=query,
            vector_rows=vector_rows,
            lexical_rows=lexical_rows,
            weights=search_options.weights,
        )

        return merged[: search_options.limit]

    def _hybrid_search_options(
        self,
        options: HybridSearchOptions | None,
        overrides: dict[str, object],
    ) -> HybridSearchOptions:
        """Normaliza opções novas e kwargs legados da busca híbrida."""

        weights = HybridSearchWeights(
            vector=float(overrides.pop("vector_weight", 0.65)),
            lexical=float(overrides.pop("lexical_weight", 0.25)),
            term_overlap=float(overrides.pop("term_overlap_weight", 0.10)),
        )

        if options is None:
            return HybridSearchOptions(weights=weights, **overrides)

        if overrides:
            return replace(options, weights=weights, **overrides)

        return options

    def get_neighbors(
        self,
        document_id: UUID,
        chunk_index: int,
        window: int,
    ) -> list[Chunk]:
        """Retorna chunks vizinhos no mesmo documento."""

        if window <= 0:
            return []

        statement = (
            select(Chunk)
            .options(selectinload(Chunk.document))
            .where(
                Chunk.document_id == document_id,
                Chunk.chunk_index >= chunk_index - window,
                Chunk.chunk_index <= chunk_index + window,
                Chunk.chunk_index != chunk_index,
            )
            .order_by(Chunk.chunk_index)
        )

        return list(self.scalars(statement))

    def _search_vector_rows(
        self,
        embedding: list[float],
        limit: int,
        max_distance: float | None,
        chunk_type: str | None,
    ) -> list[tuple[Chunk, float]]:
        """Executa a busca vetorial base."""

        distance_expression = Chunk.embedding.cosine_distance(embedding)
        distance = distance_expression.label("vector_distance")
        statement = (
            select(Chunk, distance)
            .options(selectinload(Chunk.document))
            .order_by(distance_expression)
            .limit(limit)
        )

        if chunk_type is not None:
            statement = statement.where(Chunk.chunk_type == chunk_type)

        rows = self.session.execute(statement).all()

        return [
            (chunk, float(distance))
            for chunk, distance in rows
            if max_distance is None or float(distance) <= max_distance
        ]

    def _search_lexical_rows(
        self,
        query: str,
        limit: int,
        chunk_type: str | None,
    ) -> list[tuple[Chunk, float]]:
        """Executa busca textual PostgreSQL em português."""

        if not query.strip():
            return []

        text_vector = func.to_tsvector("portuguese", Chunk.content)
        text_query = func.websearch_to_tsquery("portuguese", query)
        lexical_score = func.ts_rank_cd(text_vector, text_query).label(
            "lexical_score"
        )
        statement = (
            select(Chunk, lexical_score)
            .options(selectinload(Chunk.document))
            .where(text_vector.op("@@")(text_query))
            .order_by(lexical_score.desc(), Chunk.chunk_index)
            .limit(limit)
        )

        if chunk_type is not None:
            statement = statement.where(Chunk.chunk_type == chunk_type)

        return [
            (chunk, float(score))
            for chunk, score in self.session.execute(statement).all()
        ]

    def _merge_hybrid_rows(
        self,
        query: str,
        vector_rows: list[tuple[Chunk, float]],
        lexical_rows: list[tuple[Chunk, float]],
        weights: HybridSearchWeights,
    ) -> list[RetrievedChunk]:
        """Mescla resultados e aplica rerank determinístico."""

        by_id = self._collect_hybrid_rows(vector_rows, lexical_rows)
        results = [
            self._build_retrieved_chunk(
                query=query,
                values=values,
                weights=weights,
            )
            for values in by_id.values()
        ]

        return sorted(
            results,
            key=lambda item: (
                -item.score,
                item.vector_distance
                if item.vector_distance is not None
                else float("inf"),
                item.document_filename,
                item.chunk_index,
            ),
        )

    def _collect_hybrid_rows(
        self,
        vector_rows: list[tuple[Chunk, float]],
        lexical_rows: list[tuple[Chunk, float]],
    ) -> dict[UUID, dict[str, object]]:
        """Agrupa linhas vetoriais e lexicais pelo ID do chunk."""

        by_id: dict[UUID, dict[str, object]] = {}

        for chunk, distance in vector_rows:
            by_id.setdefault(chunk.id, {"chunk": chunk})
            by_id[chunk.id]["vector_distance"] = distance

        for chunk, score in lexical_rows:
            by_id.setdefault(chunk.id, {"chunk": chunk})
            by_id[chunk.id]["lexical_score"] = score

        return by_id

    def _build_retrieved_chunk(
        self,
        query: str,
        values: dict[str, object],
        weights: HybridSearchWeights,
    ) -> RetrievedChunk:
        """Monta um resultado recuperado com score combinado."""

        chunk = values["chunk"]
        vector_distance = values.get("vector_distance")
        lexical_score = values.get("lexical_score")
        term_overlap = self._term_overlap(query, chunk.content)
        vector_similarity = (
            1 / (1 + float(vector_distance))
            if vector_distance is not None
            else 0.0
        )
        combined_score = (
            weights.vector * vector_similarity
            + weights.lexical * float(lexical_score or 0.0)
            + weights.term_overlap * term_overlap
        )

        return RetrievedChunk(
            chunk=chunk,
            score=combined_score,
            vector_distance=(
                float(vector_distance)
                if vector_distance is not None
                else None
            ),
            lexical_score=(
                float(lexical_score)
                if lexical_score is not None
                else None
            ),
            term_overlap=term_overlap,
        )

    def _term_overlap(self, query: str, content: str) -> float:
        """Calcula fração de termos da pergunta presentes no chunk."""

        query_terms = self._normalized_terms(query)

        if not query_terms:
            return 0.0

        content_terms = self._normalized_terms(content)

        return len(query_terms & content_terms) / len(query_terms)

    def _normalized_terms(self, text: str) -> set[str]:
        """Normaliza termos para overlap lexical barato."""

        normalized = normalize("NFKD", text.lower())
        ascii_text = "".join(
            character
            for character in normalized
            if not ord(character) >= 128
        )

        return {
            term
            for term in re.findall(r"\w+", ascii_text)
            if len(term) > 2
        }
