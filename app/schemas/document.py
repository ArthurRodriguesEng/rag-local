from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """Representação HTTP de um documento ingerido."""

    id: str
    filename: str
    uploaded_at: str
