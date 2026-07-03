__all__ = [
    "PostgresConfig",
    "PostgresConnector",
    "S3Config",
    "S3Connector",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "PostgresConfig": ("src.connectors.postgres", "PostgresConfig"),
    "PostgresConnector": ("src.connectors.postgres", "PostgresConnector"),
    "S3Config": ("src.connectors.s3_storage", "S3Config"),
    "S3Connector": ("src.connectors.s3_storage", "S3Connector"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
