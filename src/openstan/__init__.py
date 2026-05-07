__all__: list[str] = ["main"]


def main() -> None:
    """Application entry point — imported lazily to avoid triggering
    bank_statement_parser's module-level side-effects before the env vars
    in __main__.py have been set."""
    from openstan.main import main as _main

    _main()
