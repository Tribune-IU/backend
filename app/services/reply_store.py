"""
Tiny in-memory store for ADK agent webhook replies.

The flow is:
  1. Backend starts an ADK session with a unique `session_id`.
  2. The ADK agent calls `submit_qa_reply` or `submit_draft_comment`, which
     POSTs back to `/v1/system:saveQaReply` or `/v1/system:saveDraftComment`.
  3. Those endpoints call `reply_store.set(session_id, text)`.
  4. The original API handler polls `reply_store.wait(session_id)` until the
     agent finishes or a timeout is reached.
"""

import asyncio
from typing import Optional


class ReplyStore:
    def __init__(self) -> None:
        self._store: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def _get_or_create(self, session_id: str) -> "asyncio.Future[str]":
        async with self._lock:
            if session_id not in self._store:
                loop = asyncio.get_event_loop()
                self._store[session_id] = loop.create_future()
            return self._store[session_id]

    async def set(self, session_id: str, value: str) -> None:
        """Called by the webhook when the agent posts its reply."""
        future = await self._get_or_create(session_id)
        if not future.done():
            future.set_result(value)

    async def wait(self, session_id: str, timeout_secs: float = 90.0) -> Optional[str]:
        """Block until the agent posts a reply or the timeout is reached."""
        future = await self._get_or_create(session_id)
        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout_secs)
        except asyncio.TimeoutError:
            return None
        finally:
            async with self._lock:
                self._store.pop(session_id, None)


# Singleton instances used by the whole backend process
qa_reply_store = ReplyStore()
draft_comment_store = ReplyStore()
