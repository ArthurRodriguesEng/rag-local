import argparse
import re
from pathlib import Path
from unicodedata import normalize

import yaml

from app.config.database import SessionLocal
from app.config.profiles import get_profile
from app.config.settings import settings
from app.services.rag import RagService
from app.services.rag_builder import (
    RagConfigOverrides,
    build_rag_config,
    build_rag_dependencies,
)


def load_cases(path: Path) -> list[dict]:
    """Carrega casos de avaliação em YAML."""

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("cases", [])


def normalize_text(text: str) -> str:
    """Normaliza texto para comparação lexical simples."""

    normalized = normalize("NFKD", text.lower())
    return "".join(
        character
        for character in normalized
        if not ord(character) >= 128
    )


def evaluate_case(case: dict, response) -> tuple[bool, list[str]]:
    """Avalia uma resposta RAG contra os critérios do caso."""

    failures = []
    chunks_text = normalize_text(
        "\n".join(chunk.content for chunk in response.chunks)
    )
    source_documents = [chunk.document_filename for chunk in response.chunks]
    answer = response.answer or ""

    expected_documents = case.get("expected_documents", [])
    if expected_documents and not any(
        document in source_documents for document in expected_documents
    ):
        failures.append(
            "documento esperado fora do top-k: "
            f"{', '.join(expected_documents)}"
        )

    for term in case.get("expected_terms", []):
        if normalize_text(term) not in chunks_text:
            failures.append(f"termo ausente nos chunks: {term}")

    if case.get("require_sources", True) and not response.chunks:
        failures.append("resposta sem fontes recuperadas")

    if case.get("require_citations", True) and response.chunks:
        if re.search(r"\[\d+\]", answer) is None:
            failures.append("resposta sem citação [n]")

    should_find_answer = case.get("should_find_answer", True)
    empty_message = settings.RAG_EMPTY_CONTEXT_MESSAGE

    if should_find_answer and empty_message in answer:
        failures.append("caso positivo respondeu contexto insuficiente")

    if not should_find_answer and response.chunks and empty_message not in answer:
        failures.append("caso negativo respondeu como se houvesse contexto")

    return not failures, failures


def run_evaluation(args: argparse.Namespace) -> int:
    """Executa avaliação local contra o RAG configurado."""

    cases = load_cases(Path(args.cases))
    profile = get_profile(args.profile)
    session = SessionLocal()
    failures = 0

    try:
        service = RagService(
            session=session,
            dependencies=build_rag_dependencies(
                session=session,
                embedding_model=args.embedding_model or profile.embedding_model,
                chat_model=args.chat_model or profile.chat_model,
            ),
            config=build_rag_config(
                profile=profile,
                overrides=RagConfigOverrides(limit=args.limit),
            ),
        )

        for index, case in enumerate(cases, start=1):
            response = service.answer(
                question=case["question"],
                limit=args.limit,
            )
            passed, case_failures = evaluate_case(case, response)
            status = "PASS" if passed else "FAIL"
            print(f"{status} {index:02d} {case.get('name', case['question'])}")

            for failure in case_failures:
                print(f"  - {failure}")

            failures += 0 if passed else 1

    finally:
        session.close()

    print(f"\nCasos: {len(cases)} | Falhas: {failures}")
    return 1 if failures else 0


def build_parser() -> argparse.ArgumentParser:
    """Cria parser do avaliador."""

    parser = argparse.ArgumentParser(
        description="Avalia qualidade local do RAG com casos YAML.",
    )
    parser.add_argument(
        "--cases",
        default="scripts/evaluation_cases.yaml",
        help="Arquivo YAML com os casos de avaliação.",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="Perfil RAG usado na avaliação.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Top-k de chunks usados por pergunta.",
    )
    parser.add_argument(
        "--chat-model",
        default=None,
        help="Modelo de chat local usado na avaliação.",
    )
    parser.add_argument(
        "--embedding-model",
        default=None,
        help="Modelo de embedding local usado na avaliação.",
    )

    return parser


def main() -> None:
    """Ponto de entrada do avaliador."""

    raise SystemExit(run_evaluation(build_parser().parse_args()))


if __name__ == "__main__":
    main()
