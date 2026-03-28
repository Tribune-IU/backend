import logging

import httpx
from app.api.errors import ApiError

logger = logging.getLogger(__name__)

ADK_SERVER_URL = "http://127.0.0.1:8080"


import uuid

async def call_adk_agent(app_name: str, message: str) -> None:
    """Call an ADK agent by generating a session, initializing it, and then running the agent."""
    session_id = str(uuid.uuid4())
    user_id = "system"
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # First create the session
            session_url = f"{ADK_SERVER_URL}/apps/{app_name}/users/{user_id}/sessions"
            session_payload = {"sessionId": session_id}
            session_resp = await client.post(session_url, json=session_payload)
            session_resp.raise_for_status()

            # Now run the agent with the initialized session
            payload = {
                "appName": app_name,
                "userId": user_id,
                "sessionId": session_id,
                "newMessage": {
                    "role": "user",
                    "parts": [{"text": message}]
                }
            }
            
            response = await client.post(f"{ADK_SERVER_URL}/run", json=payload)
            response.raise_for_status()
            logger.info("Agent %s completed its run with session %s.", app_name, session_id)
    except Exception as e:
        logger.error("Failed to call ADK agent %s: %s", app_name, e)
        raise ApiError(http_status=500, status="INTERNAL", message=f"Failed to call agent: {e}")


async def trigger_profile_agent(user_id: str, bio: str) -> None:
    """Call profile_agent, explicitly passing the user_id in the text prompt so the tool can use it."""
    prompt = f"Target User ID: {user_id}\n\nUser Bio: {bio}"
    await call_adk_agent("profile_agent", prompt)


async def trigger_monitor_agent(title: str, source: str, document_text: str) -> None:
    """Call monitor_agent to extract metadata and push it back via API."""
    prompt = f"Original Title: {title}\nOriginal Source: {source}\n\nPlease parse the following text:\n\n{document_text}"
    await call_adk_agent("monitor_agent", prompt)
