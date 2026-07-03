__all__ = ["PostgresConfig", "PostgresConnector"]


def __getattr__(name: str):
    if name in __all__:
        from src.connectors.postgres import PostgresConfig, PostgresConnector

        return {"PostgresConfig": PostgresConfig, "PostgresConnector": PostgresConnector}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
