from app.config.settings import settings


def info(message: str) -> None:
    print(f"[INFO] {message}")


def success(message: str) -> None:
    print(f"[OK] {message}")


def warning(message: str) -> None:
    print(f"[WARN] {message}")


def debug(message: str) -> None:
    if settings.DEBUG:
        print(f"[DEBUG] {message}")
