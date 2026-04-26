"""Smoke test: the web package imports."""


def test_web_package_imports():
    import canastra.web

    assert hasattr(canastra.web, "__name__")


def test_create_app_is_exported():
    from canastra.web import create_app

    assert callable(create_app)
