import pytest
from core.context_store import get_context_store


def test_append_and_get():
    store = get_context_store()
    store.delete("test-session")
    store.append("test-session", "Hello there")
    store.append("test-session", "Are you hungry?")
    ctx = store.get("test-session")
    assert ctx == ["Hello there", "Are you hungry?"]


def test_max_five_utterances():
    store = get_context_store()
    store.delete("test-session-2")
    for i in range(8):
        store.append("test-session-2", f"utterance {i}")
    ctx = store.get("test-session-2")
    assert len(ctx) == 5
    assert ctx[0] == "utterance 3"
    assert ctx[-1] == "utterance 7"


def test_get_missing_session_returns_empty():
    store = get_context_store()
    assert store.get("nonexistent-xyz") == []


def test_delete_clears_session():
    store = get_context_store()
    store.append("del-session", "something")
    store.delete("del-session")
    assert store.get("del-session") == []
