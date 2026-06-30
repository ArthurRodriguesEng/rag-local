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
            "documents/notas.md",
            "--chunk-size",
            "800",
            "--chunk-overlap",
            "120",
            "--embedding-model",
            "bge-m3",
        ]
    )

    assert args.command == "ingest"
    assert args.file_path == [
        "documents/manual_python.txt",
        "documents/notas.md",
    ]
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
            "--chat-model",
            "llama3.2:3b",
            "--embedding-model",
            "bge-m3",
            "--system-prompt",
            "Responda com base no contexto.",
            "--profile",
            "fast",
            "--response-mode",
            "deep",
            "--memory-limit",
            "6",
            "--memory-max-chars",
            "1600",
        ]
    )

    assert args.command == "ask"
    assert args.question == ["Como", "usar", "Python?"]
    assert args.limit == 3
    assert args.chat_model == "llama3.2:3b"
    assert args.embedding_model == "bge-m3"
    assert args.system_prompt == "Responda com base no contexto."
    assert args.profile == "fast"
    assert args.response_mode == "deep"
    assert args.memory_limit == 6
    assert args.memory_max_chars == 1600


def test_parser_accepts_chat_command_with_profile() -> None:
    parser = cli.build_parser()

    args = parser.parse_args(
        [
            "chat",
            "--profile",
            "balanced",
            "--limit",
            "4",
            "--response-mode",
            "analytical",
            "--memory-limit",
            "4",
        ]
    )

    assert args.command == "chat"
    assert args.profile == "balanced"
    assert args.limit == 4
    assert args.response_mode == "analytical"
    assert args.memory_limit == 4


def test_chat_error_help_for_killed_model_suggests_lighter_run(capsys) -> None:
    cli._print_chat_error_help(
        error_message="llama-server process has terminated: signal: killed",
        selected_chat_model="deepseek-r1:8b",
        profile_name="reasoning",
    )

    output = capsys.readouterr().out

    assert "falta de memória" in output
    assert "--profile fast --limit 2" in output
    assert "--chat-model qwen3:8b --limit 2" in output
    assert "ollama pull deepseek-r1:8b" not in output


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
