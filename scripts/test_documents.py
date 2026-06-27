from app.config.database import SessionLocal
from app.models.document import Document

session = SessionLocal()

document = Document(filename="manual_python.pdf")

session.add(document)
session.commit()

print(document.id)
