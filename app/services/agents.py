import logging
import uuid
import json

import httpx
from app.api.errors import ApiError

logger = logging.getLogger(__name__)

ADK_SERVER_URL = "http://127.0.0.1:8080"


async def call_adk_agent_fire_and_forget(app_name: str, message: str) -> None:
    """Call an ADK agent via /run (fire-and-forget, no response needed).
    Used by monitor_agent and profile_agent which post back via their own webhooks.
    """
    session_id = str(uuid.uuid4())
    user_id = "system"

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            session_url = f"{ADK_SERVER_URL}/apps/{app_name}/users/{user_id}/sessions"
            session_resp = await client.post(session_url, json={"sessionId": session_id})
            session_resp.raise_for_status()

            payload = {
                "appName": app_name,
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {"role": "user", "parts": [{"text": message}]},
            }
            response = await client.post(f"{ADK_SERVER_URL}/run", json=payload)
            response.raise_for_status()
            logger.info("Agent %s completed its run with session %s.", app_name, session_id)
    except Exception as e:
        logger.error("Failed to call ADK agent %s: %s", app_name, e)
        raise ApiError(http_status=500, status="INTERNAL", message=f"Failed to call agent: {e}")


async def call_adk_agent(app_name: str, message: str) -> None:
    """Alias kept for backward-compat with monitor_agent / profile_agent callers."""
    await call_adk_agent_fire_and_forget(app_name, message)


async def call_adk_agent_and_get_reply(app_name: str, message: str, timeout: float = 90.0) -> str:
    """Call an ADK agent via /run_sse and stream the reply back directly.

    Collects all text parts emitted by the agent and returns them joined as a
    single string.  This avoids the webhook roundtrip pattern that depends on
    the model reliably calling a specific tool.

    Returns the concatenated agent text or raises ApiError on failure/timeout.
    """
    session_id = str(uuid.uuid4())
    user_id = "system"

    async with httpx.AsyncClient(timeout=timeout + 10) as client:
        # Create session
        session_url = f"{ADK_SERVER_URL}/apps/{app_name}/users/{user_id}/sessions"
        try:
            sr = await client.post(session_url, json={"sessionId": session_id})
            sr.raise_for_status()
        except Exception as e:
            raise ApiError(http_status=502, status="UNAVAILABLE", message=f"ADK session error: {e}")

        payload = {
            "appName": app_name,
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {"role": "user", "parts": [{"text": message}]},
        }

        text_parts: list[str] = []
        try:
            async with client.stream(
                "POST",
                f"{ADK_SERVER_URL}/run_sse",
                json=payload,
                timeout=timeout,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if not data_str:
                        continue
                    try:
                        obj = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    if obj.get("error"):
                        raise ApiError(
                            http_status=502,
                            status="UNAVAILABLE",
                            message=f"ADK agent error: {obj['error']}",
                        )

                    # Collect model text parts (role == "model")
                    content = obj.get("content", {})
                    if content.get("role") == "model":
                        for part in content.get("parts", []):
                            if "text" in part and part["text"].strip():
                                text_parts.append(part["text"].strip())

        except httpx.TimeoutException:
            raise ApiError(
                http_status=504,
                status="DEADLINE_EXCEEDED",
                message=f"Agent '{app_name}' did not respond within {timeout:.0f}s.",
            )
        except ApiError:
            raise
        except Exception as e:
            raise ApiError(http_status=502, status="UNAVAILABLE", message=f"ADK stream error: {e}")

    if not text_parts:
        raise ApiError(
            http_status=502,
            status="UNAVAILABLE",
            message=f"Agent '{app_name}' returned no text.",
        )

    return "\n\n".join(text_parts)


# ---------------------------------------------------------------------------
# High-level helpers
# ---------------------------------------------------------------------------

async def trigger_profile_agent(user_id: str, bio: str) -> None:
    """Call profile_agent, explicitly passing the user_id in the text prompt so the tool can use it."""
    prompt = f"Target User ID: {user_id}\n\nUser Bio: {bio}"
    await call_adk_agent_fire_and_forget("profile_agent", prompt)


async def trigger_monitor_agent(title: str, source: str, document_text: str) -> None:
    """Call monitor_agent to extract metadata and push it back via API."""
    prompt = f"Original Title: {title}\nOriginal Source: {source}\n\nPlease parse the following text:\n\n{document_text}"
    await call_adk_agent_fire_and_forget("monitor_agent", prompt)


async def trigger_document_qa_agent(
    session_id: str,
    document_context: str,
    question: str,
    history: list[dict] | None = None,
) -> str:
    """Call document_qa_agent and return its answer directly via SSE streaming.

    The `session_id` parameter is kept in the signature so the documents API
    can use it in the reply_store if desired, but this implementation returns
    the text inline.
    """
    history_block = ""
    if history:
        lines = []
        for turn in history:
            role = "Resident" if turn.get("role") == "user" else "Assistant"
            lines.append(f"{role}: {turn.get('text', '')}")
        history_block = "--- CONVERSATION HISTORY ---\n" + "\n".join(lines) + "\n\n"

    prompt = (
        f"--- DOCUMENT CONTEXT ---\n{document_context}\n\n"
        + history_block
        + f"--- RESIDENT QUESTION ---\n{question}\n\n"
        "Answer the question using only the document context above."
    )
    return await call_adk_agent_and_get_reply("document_qa_agent", prompt)


async def trigger_draft_comment_agent(
    session_id: str,
    document_summary: str,
    conversation: list[dict],
    resident_context: str = "",
) -> str:
    """Call draft_comment_agent and return the drafted letter directly via SSE streaming."""
    transcript_lines = []
    for turn in conversation:
        role = "Resident" if turn.get("role") == "user" else "Assistant"
        transcript_lines.append(f"{role}: {turn.get('text', '')}")
    transcript = "\n".join(transcript_lines) or "(no prior conversation)"

    prompt = (
        f"--- DOCUMENT SUMMARY ---\n{document_summary}\n\n"
        f"--- CONVERSATION TRANSCRIPT ---\n{transcript}\n\n"
        + (f"--- RESIDENT CONTEXT ---\n{resident_context}\n\n" if resident_context else "")
        + "Draft a public comment letter based on the above."
    )
    return await call_adk_agent_and_get_reply("draft_comment_agent", prompt)
