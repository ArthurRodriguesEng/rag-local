from fastapi import FastAPI

from app.api.router import api_router


def create_app() -> FastAPI:
    """Cria e configura a aplicação HTTP."""

    application = FastAPI(title="rag-local")
    application.include_router(api_router)

    return application


app = create_app()
