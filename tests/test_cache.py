import pytest

from src.utils.cache import TTLCache, make_cache_key, query_cache


def test_cache_set_and_get_value():
    cache = TTLCache[str](default_ttl_seconds=60)

    cache.set("question-1", "cached-result")

    assert cache.get("question-1") == "cached-result"


def test_cache_returns_none_for_missing_key():
    cache = TTLCache[str](default_ttl_seconds=60)

    assert cache.get("missing") is None


def test_cache_expires_value():
    fake_time = {"now": 100.0}

    def time_provider() -> float:
        return fake_time["now"]

    cache = TTLCache[str](
        default_ttl_seconds=10,
        time_provider=time_provider,
    )

    cache.set("question-1", "cached-result")
    assert cache.get("question-1") == "cached-result"

    fake_time["now"] = 111.0

    assert cache.get("question-1") is None


def test_cache_delete_removes_value():
    cache = TTLCache[str](default_ttl_seconds=60)

    cache.set("question-1", "cached-result")

    assert cache.delete("question-1") is True
    assert cache.get("question-1") is None


def test_cache_clear_removes_all_values():
    cache = TTLCache[str](default_ttl_seconds=60)

    cache.set("question-1", "result-1")
    cache.set("question-2", "result-2")

    cache.clear()

    assert len(cache) == 0


def test_cache_evicts_oldest_item_when_max_size_is_reached():
    fake_time = {"now": 100.0}

    def time_provider() -> float:
        return fake_time["now"]

    cache = TTLCache[str](
        default_ttl_seconds=60,
        max_size=2,
        time_provider=time_provider,
    )

    cache.set("first", "result-1")

    fake_time["now"] = 101.0
    cache.set("second", "result-2")

    fake_time["now"] = 102.0
    cache.set("third", "result-3")

    assert cache.get("first") is None
    assert cache.get("second") == "result-2"
    assert cache.get("third") == "result-3"


def test_make_cache_key_is_deterministic():
    first_key = make_cache_key(
        "chat",
        "sess_abc123",
        "Son 3 ayda en yüksek ciro hangi kategoride?",
        include_sql=True,
    )
    second_key = make_cache_key(
        "chat",
        "sess_abc123",
        "Son 3 ayda en yüksek ciro hangi kategoride?",
        include_sql=True,
    )

    assert first_key == second_key


def test_make_cache_key_changes_when_input_changes():
    first_key = make_cache_key("chat", "sess_1", "question")
    second_key = make_cache_key("chat", "sess_2", "question")

    assert first_key != second_key


def test_cache_rejects_invalid_ttl():
    with pytest.raises(ValueError):
        TTLCache(default_ttl_seconds=0)


def test_cache_rejects_invalid_max_size():
    with pytest.raises(ValueError):
        TTLCache(max_size=0)


def test_module_level_query_cache_is_available():
    query_cache.clear()

    query_cache.set("sample-key", {"answer": "cached"})

    assert query_cache.get("sample-key") == {"answer": "cached"}

    query_cache.clear()