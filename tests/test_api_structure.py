from app.main import create_app


def test_create_app_registers_expected_routes() -> None:
    application = create_app()
    routes = set(application.openapi()["paths"])

    assert application.title == "rag-local"
    assert "/health" in routes
    assert "/documents" in routes
    assert "/documents/upload" in routes
    assert "/documents/{document_id}" in routes
    assert "/chat" in routes
