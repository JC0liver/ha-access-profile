"""Finish Home Assistant onboarding for the ap-testbed via the onboarding HTTP API.

Creates a local owner user with a random password, completes core_config,
analytics and integration steps, then creates a long-lived access token.
Writes the password and token to .secrets.env next to this script.
Never prints secrets.

Run with the testbed venv:  .venv\\Scripts\\python.exe onboard.py
"""
from __future__ import annotations

import asyncio
import json
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import websockets

BASE = "http://127.0.0.1:8124"
WS = "ws://127.0.0.1:8124/api/websocket"
CLIENT_ID = f"{BASE}/"
USERNAME = "testbed"
HERE = Path(__file__).resolve().parent
SECRETS = HERE / ".secrets.env"


def req(method: str, path: str, data=None, token: str | None = None, form: bool = False):
    headers = {}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            print(f"{method} {path} -> HTTP {resp.status}")
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        print(f"{method} {path} -> HTTP {e.code}: {e.read()[:300]!r}")
        raise


def exchange_code(code: str) -> dict:
    _, tok = req(
        "POST",
        "/auth/token",
        {"grant_type": "authorization_code", "code": code, "client_id": CLIENT_ID},
        form=True,
    )
    return tok


async def long_lived_token(access_token: str) -> str:
    async with websockets.connect(WS) as ws:
        msg = json.loads(await ws.recv())
        assert msg["type"] == "auth_required", msg
        await ws.send(json.dumps({"type": "auth", "access_token": access_token}))
        msg = json.loads(await ws.recv())
        if msg["type"] != "auth_ok":
            raise RuntimeError(f"websocket auth failed: {msg.get('type')}")
        await ws.send(
            json.dumps(
                {
                    "id": 1,
                    "type": "auth/long_lived_access_token",
                    "client_name": "ap-testbed",
                    "lifespan": 3650,
                }
            )
        )
        msg = json.loads(await ws.recv())
        if not msg.get("success"):
            raise RuntimeError(f"long-lived token failed: {msg.get('error')}")
        print("WS auth/long_lived_access_token -> success")
        return msg["result"]


def main() -> int:
    _, status = req("GET", "/api/onboarding")
    done = {s["step"] for s in status if s["done"]}
    print(f"onboarding steps already done: {sorted(done) or 'none'}")
    if "user" in done:
        print("User step already done; onboarding was run before. Not touching .secrets.env.")
        return 0 if done >= {"user", "core_config", "analytics", "integration"} else 1

    password = secrets.token_urlsafe(24)
    _, res = req(
        "POST",
        "/api/onboarding/users",
        {
            "client_id": CLIENT_ID,
            "name": "Testbed Owner",
            "username": USERNAME,
            "password": password,
            "language": "en",
        },
    )
    # Save password right away so a later failure doesn't lose it.
    SECRETS.write_text(
        f"HA_URL={BASE}\nHA_USERNAME={USERNAME}\nHA_PASSWORD={password}\n", encoding="utf-8"
    )
    tok = exchange_code(res["auth_code"])
    access = tok["access_token"]

    req("POST", "/api/onboarding/core_config", {}, token=access)
    req("POST", "/api/onboarding/analytics", {}, token=access)
    _, res = req(
        "POST",
        "/api/onboarding/integration",
        {"client_id": CLIENT_ID, "redirect_uri": f"{BASE}/?auth_callback=1"},
        token=access,
    )
    # Exchange the integration-step code too (what the frontend does).
    exchange_code(res["auth_code"])

    llat = asyncio.run(long_lived_token(access))
    with SECRETS.open("a", encoding="utf-8") as f:
        f.write(f"HA_TOKEN={llat}\n")

    _, status = req("GET", "/api/onboarding")
    pending = [s["step"] for s in status if not s["done"]]
    print(f"onboarding steps pending after run: {pending or 'none'}")
    print(f"credentials written to {SECRETS}")
    return 0 if not pending else 1


if __name__ == "__main__":
    sys.exit(main())
