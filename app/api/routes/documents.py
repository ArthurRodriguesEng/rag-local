from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_session
from app.config.settings import settings
from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentResponse
from app.services.ingestion import IngestionService


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    filename: str,
    request: Request,
    session: Session = Depends(get_session),
) -> DocumentResponse:
    """Recebe um arquivo, salva localmente e executa ingestão."""

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / Path(filename).name

    with file_path.open("wb") as output:
        output.write(await request.body())

    document = IngestionService(session).ingest(str(file_path))

    return DocumentResponse(
        id=str(document.id),
        filename=document.filename,
        uploaded_at=document.uploaded_at.isoformat(),
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    session: Session = Depends(get_session),
) -> list[DocumentResponse]:
    """Lista documentos ingeridos."""

    documents = DocumentRepository(session).list_all()

    return [
        DocumentResponse(
            id=str(document.id),
            filename=document.filename,
            uploaded_at=document.uploaded_at.isoformat(),
        )
        for document in documents
    ]


@router.delete("/{document_id}")
def delete_document(
    document_id: UUID,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Remove um documento e seus chunks."""

    repository = DocumentRepository(session)
    document = repository.get_by_id(document_id)

    if document is None:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    repository.delete(document)
    repository.commit()

    return {"status": "deleted"}
