import time
from collections import deque
from functools import lru_cache

_TTL_SECONDS = 600  # 10 minutes, matches session store TTL


class ContextStore:
    def __init__(self):
        # {session_id: {"texts": deque(maxlen=5), "last_access": float}}
        self._store: dict[str, dict] = {}

    def _touch(self, session_id: str) -> None:
        if session_id not in self._store:
            self._store[session_id] = {"texts": deque(maxlen=5), "last_access": time.time()}
        else:
            self._store[session_id]["last_access"] = time.time()

    def append(self, session_id: str, text: str) -> None:
        self._touch(session_id)
        self._store[session_id]["texts"].append(text)
        self._purge_stale()

    def get(self, session_id: str) -> list[str]:
        if session_id not in self._store:
            return []
        self._touch(session_id)
        return list(self._store[session_id]["texts"])

    def delete(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def _purge_stale(self) -> None:
        cutoff = time.time() - _TTL_SECONDS
        stale = [sid for sid, v in self._store.items() if v["last_access"] < cutoff]
        for sid in stale:
            del self._store[sid]


@lru_cache(maxsize=1)
def get_context_store() -> ContextStore:
    return ContextStore()
