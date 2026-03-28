import asyncio
import httpx
import json

BACKEND = "http://127.0.0.1:8000"

async def wait_for_profile(client, user_id, timeout=60):
    """Poll until the async profile agent has written non-empty tags."""
    for i in range(timeout):
        res = await client.get(f"{BACKEND}/v1/users/{user_id}")
        if res.status_code == 200:
            profile = res.json().get("user", {}).get("parsed_profile", {})
            tags = [v for lst in profile.values() for v in (lst if isinstance(lst, list) else [lst])]
            if tags:
                print(f"   [profile ready after {i+1}s] tags: {tags}")
                return True
        await asyncio.sleep(1)
    print("   [WARN] Profile tags still empty after timeout!")
    return False

async def wait_for_alerts(client, user_id, timeout=15):
    """Poll for alerts once the profile is known to have tags."""
    for _ in range(timeout):
        res = await client.get(f"{BACKEND}/v1/users/{user_id}/alerts")
        alerts = res.json()["alerts"]
        if alerts:
            return alerts
        await asyncio.sleep(1)
    return []

async def test_flow():
    bio = "I am a grad student living off campus. I care heavily about housing affordability and transit infrastructure."
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("[1] Creating new User...")
        res = await client.post(f"{BACKEND}/v1/users", json={"bio": bio})
        res.raise_for_status()
        user = res.json()["user"]
        user_id = user["id"]
        print(f"   -> User ID: {user_id}")

        print("[2] Waiting for Profile Agent to finish (async webhook — up to 60s)...")
        profile_ready = await wait_for_profile(client, user_id)

        if profile_ready:
            print("[2b] Profile tagged — checking for immediate onboarding alerts...")
            alerts = await wait_for_alerts(client, user_id)
            print(f"   -> [ONBOARDING] Found {len(alerts)} alerts from existing seed docs!")
            print(json.dumps(alerts, indent=2))
        else:
            print("   -> Skipping alert check (profile never got tags)")

        print("\n[3] Triggering Monitor Stub (loads seed JSONs as scraper proxy)...")
        res = await client.post(f"{BACKEND}/v1/system:triggerMonitor")
        res.raise_for_status()
        body = res.json()
        print(f"   -> Status: {body['status']} | {body['message']}")

        print("[4] Final alert count for this user...")
        res = await client.get(f"{BACKEND}/v1/users/{user_id}/alerts")
        alerts2 = res.json()["alerts"]
        print(f"   -> Total alerts: {len(alerts2)}")
        print(json.dumps(alerts2, indent=2))

if __name__ == "__main__":
    asyncio.run(test_flow())
