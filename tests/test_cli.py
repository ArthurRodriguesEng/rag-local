from app import cli


class FakeSession:
    """Sessão falsa usada para validar comandos transacionais da CLI."""

    def __init__(self) -> None:
        self.statements = []
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def execute(self, statement) -> None:
        self.statements.append(statement)

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


def test_parser_accepts_ingest_command() -> None:
    parser = cli.build_parser()

    args = parser.parse_args(
        [
            "ingest",
            "documents/manual_python.txt",
            "--chunk-size",
            "800",
            "--chunk-overlap",
            "120",
            "--embedding-model",
            "bge-m3",
        ]
    )

    assert args.command == "ingest"
    assert args.file_path == "documents/manual_python.txt"
    assert args.chunk_size == 800
    assert args.chunk_overlap == 120
    assert args.embedding_model == "bge-m3"


def test_parser_accepts_ask_command_with_limit() -> None:
    parser = cli.build_parser()

    args = parser.parse_args(
        [
            "ask",
            "Como",
            "usar",
            "Python?",
            "--limit",
            "3",
            "--chat-provider",
            "openai",
            "--chat-model",
            "gpt-test",
            "--embedding-model",
            "bge-m3",
            "--system-prompt",
            "Responda com base no contexto.",
            "--profile",
            "fast_local",
            "--response-mode",
            "deep",
        ]
    )

    assert args.command == "ask"
    assert args.question == ["Como", "usar", "Python?"]
    assert args.limit == 3
    assert args.chat_provider == "openai"
    assert args.chat_model == "gpt-test"
    assert args.embedding_model == "bge-m3"
    assert args.system_prompt == "Responda com base no contexto."
    assert args.profile == "fast_local"
    assert args.response_mode == "deep"


def test_parser_accepts_chat_command_with_profile() -> None:
    parser = cli.build_parser()

    args = parser.parse_args(
        [
            "chat",
            "--profile",
            "balanced_local",
            "--limit",
            "4",
            "--response-mode",
            "analytical",
        ]
    )

    assert args.command == "chat"
    assert args.profile == "balanced_local"
    assert args.limit == 4
    assert args.response_mode == "analytical"


def test_parser_accepts_reset_db_command() -> None:
    parser = cli.build_parser()

    args = parser.parse_args(
        [
            "reset-db",
            "--yes",
        ]
    )

    assert args.command == "reset-db"
    assert args.yes is True


def test_clear_db_deletes_chunks_and_documents(monkeypatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(
        cli,
        "SessionLocal",
        lambda: session,
    )

    cli.clear_db()

    assert len(session.statements) == 2
    assert session.committed is True
    assert session.rolled_back is False
    assert session.closed is True
