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


@router.post("/upload/batch", response_model=list[DocumentResponse])
async def upload_documents(
    request: Request,
    session: Session = Depends(get_session),
) -> list[DocumentResponse]:
    """Recebe múltiplos arquivos multipart e executa ingestão em lote."""

    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    form = await request.form()
    upload_files = []

    for field_name in form:
        for value in form.getlist(field_name):
            if hasattr(value, "filename") and hasattr(value, "read"):
                upload_files.append(value)

    if not upload_files:
        raise HTTPException(
            status_code=400,
            detail="Envie um ou mais arquivos multipart.",
        )

    file_paths = []

    for upload_file in upload_files:
        if not upload_file.filename:
            continue

        file_path = upload_dir / Path(upload_file.filename).name

        with file_path.open("wb") as output:
            output.write(await upload_file.read())

        await upload_file.close()
        file_paths.append(str(file_path))

    if not file_paths:
        raise HTTPException(
            status_code=400,
            detail="Nenhum arquivo válido foi enviado.",
        )

    documents = IngestionService(session).ingest_many(file_paths)

    return [
        DocumentResponse(
            id=str(document.id),
            filename=document.filename,
            uploaded_at=document.uploaded_at.isoformat(),
        )
        for document in documents
    ]


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
