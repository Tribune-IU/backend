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
            logger.info("ADK   %s  creating session  session=%s", app_name, session_id)
            session_resp = await client.post(session_url, json={"sessionId": session_id})
            session_resp.raise_for_status()

            payload = {
                "appName": app_name,
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {"role": "user", "parts": [{"text": message}]},
            }
            logger.info("ADK   %s  POST /run  session=%s  prompt_len=%d", app_name, session_id, len(message))
            response = await client.post(f"{ADK_SERVER_URL}/run", json=payload)
            response.raise_for_status()
            logger.info("ADK   %s  /run complete  session=%s", app_name, session_id)
    except Exception as e:
        logger.error("ADK   %s  failed  session=%s  error=%s", app_name, session_id, e)
        raise ApiError(http_status=500, status="INTERNAL", message=f"Failed to call agent: {e}")


async def call_adk_agent(app_name: str, message: str) -> None:
    """Alias kept for backward-compat with monitor_agent / profile_agent callers."""
    await call_adk_agent_fire_and_forget(app_name, message)


async def call_adk_agent_and_get_reply(app_name: str, message: str, timeout: float = 90.0) -> str:
    """Call an ADK agent via /run and return the model's text reply.

    Uses the synchronous /run endpoint which returns all events as a JSON list.
    Collects the last model text part and returns it.
    """
    session_id = str(uuid.uuid4())
    user_id = "system"

    async with httpx.AsyncClient(timeout=timeout + 10) as client:
        session_url = f"{ADK_SERVER_URL}/apps/{app_name}/users/{user_id}/sessions"
        logger.info("ADK   %s  creating session  session=%s", app_name, session_id)
        try:
            sr = await client.post(session_url, json={"sessionId": session_id})
            sr.raise_for_status()
        except Exception as e:
            logger.error("ADK   %s  session create failed  session=%s  error=%s", app_name, session_id, e)
            raise ApiError(http_status=502, status="UNAVAILABLE", message=f"ADK session error: {e}")

        payload = {
            "appName": app_name,
            "userId": user_id,
            "sessionId": session_id,
            "newMessage": {"role": "user", "parts": [{"text": message}]},
        }

        logger.info("ADK   %s  POST /run  session=%s  prompt_len=%d  timeout=%.0fs", app_name, session_id, len(message), timeout)
        try:
            resp = await client.post(f"{ADK_SERVER_URL}/run", json=payload, timeout=timeout)
            resp.raise_for_status()
            events = resp.json()
        except httpx.TimeoutException:
            raise ApiError(
                http_status=504,
                status="DEADLINE_EXCEEDED",
                message=f"Agent '{app_name}' did not respond within {timeout:.0f}s.",
            )
        except Exception as e:
            logger.error("ADK   %s  /run failed  session=%s  error=%s", app_name, session_id, e)
            raise ApiError(http_status=502, status="UNAVAILABLE", message=f"ADK run error: {e}")

    logger.info("ADK   %s  /run returned %d events  session=%s", app_name, len(events), session_id)
    text_parts: list[str] = []
    for event in events:
        content = event.get("content", {})
        if content.get("role") == "model":
            for part in content.get("parts", []):
                if "text" in part and part["text"].strip():
                    text_parts.append(part["text"].strip())

    if not text_parts:
        logger.warning("ADK   %s  no text in reply  session=%s  events=%d", app_name, session_id, len(events))
        raise ApiError(
            http_status=502,
            status="UNAVAILABLE",
            message=f"Agent '{app_name}' returned no text.",
        )

    reply = "\n\n".join(text_parts)
    logger.info("ADK   %s  reply ready  session=%s  reply_len=%d", app_name, session_id, len(reply))
    return reply


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


def _profile_block(user_profile: dict | None) -> str:
    if not user_profile:
        return ""
    lines = [f"{k}: {', '.join(v)}" for k, v in user_profile.items() if v]
    return ("--- RESIDENT PROFILE ---\n" + "\n".join(lines) + "\n\n") if lines else ""


async def trigger_document_qa_agent(
    session_id: str,
    document_context: str,
    question: str,
    history: list[dict] | None = None,
    user_profile: dict | None = None,
) -> str:
    history_block = ""
    if history:
        lines = []
        for turn in history:
            role = "Resident" if turn.get("role") == "user" else "Assistant"
            lines.append(f"{role}: {turn.get('text', '')}")
        history_block = "--- CONVERSATION HISTORY ---\n" + "\n".join(lines) + "\n\n"

    prompt = (
        f"--- DOCUMENT CONTEXT ---\n{document_context}\n\n"
        + _profile_block(user_profile)
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
    user_profile: dict | None = None,
) -> str:
    """Call draft_comment_agent and return the drafted letter via the reply store.

    The agent calls submit_draft_comment(session_id, draft) which POSTs back to
    /v1/system:saveDraftComment. That webhook sets draft_comment_store so we can
    retrieve the actual draft text here.
    """
    from app.services.reply_store import draft_comment_store

    transcript_lines = []
    for turn in conversation:
        role = "Resident" if turn.get("role") == "user" else "Assistant"
        transcript_lines.append(f"{role}: {turn.get('text', '')}")
    transcript = "\n".join(transcript_lines) or "(no prior conversation)"

    prompt = (
        f"Session ID: {session_id}\n\n"
        f"--- DOCUMENT SUMMARY ---\n{document_summary}\n\n"
        + _profile_block(user_profile)
        + f"--- CONVERSATION TRANSCRIPT ---\n{transcript}\n\n"
        + (f"--- RESIDENT CONTEXT ---\n{resident_context}\n\n" if resident_context else "")
        + "Draft a public comment letter based on the above, then call submit_draft_comment."
    )

    # /run is synchronous — by the time it returns the tool has already POSTed to the webhook
    await call_adk_agent_and_get_reply("draft_comment_agent", prompt)

    draft = await draft_comment_store.wait(session_id, timeout_secs=5.0)
    if not draft:
        raise ApiError(
            http_status=502,
            status="UNAVAILABLE",
            message="draft_comment_agent did not submit a draft.",
        )
    return draft
