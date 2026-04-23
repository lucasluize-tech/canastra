"""Scaffold smoke test: package importable, run() callable exists."""


def test_cli_package_imports() -> None:
    import canastra.cli  # noqa: F401


def test_run_symbol_exists() -> None:
    from canastra.cli import run

    assert callable(run)
