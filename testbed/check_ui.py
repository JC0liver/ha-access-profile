"""API load check and headless screenshots for the access_profile UI integration.

Called by check-ui.ps1 after the container has been restarted with the UI mounts.
Uses Playwright's bundled Chromium, headless. Never uses Microsoft Edge.
Never prints the token or password.

  .venv\\Scripts\\python.exe -I check_ui.py [--out screenshots] [--no-create-entry]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

import websockets
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8124"
WS = "ws://127.0.0.1:8124/api/websocket"
DOMAIN = "access_profile"
HERE = Path(__file__).resolve().parent


def load_secrets() -> dict:
    out = {}
    for line in (HERE / ".secrets.env").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def api(method: str, path: str, token: str, data=None):
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(
        BASE + path,
        data=body,
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        return e.code, e.read()[:500].decode(errors="replace")


async def ws_calls(token: str, calls: list[dict]) -> list[dict]:
    results = []
    async with websockets.connect(WS, max_size=None) as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "auth", "access_token": token}))
        if json.loads(await ws.recv())["type"] != "auth_ok":
            raise RuntimeError("websocket auth failed")
        for i, c in enumerate(calls, start=1):
            await ws.send(json.dumps({"id": i, **c}))
            while True:
                msg = json.loads(await ws.recv())
                if msg.get("id") == i and msg.get("type") == "result":
                    results.append(msg)
                    break
    return results


def screenshot(token: str, pages: list[tuple[str, str]], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    saved = []
    tokens = {
        "hassUrl": BASE,
        "clientId": f"{BASE}/",
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 315360000,
        "refresh_token": "",
        "expires": 4102444800000,
    }
    with sync_playwright() as p:
        # Bundled Chromium only; no channel= argument, so Edge/Chrome are never used.
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1400, "height": 900}, color_scheme="light")
        ctx.add_init_script(
            "try{localStorage.setItem('hassTokens', %s);"
            "localStorage.setItem('selectedLanguage','\"en\"');}catch(e){}" % json.dumps(json.dumps(tokens))
        )
        page = ctx.new_page()
        for name, path in pages:
            page.goto(BASE + path, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(4000)
            dest = out / f"{name}.png"
            page.screenshot(path=str(dest), full_page=True)
            print(f"screenshot {path} -> {dest}")
            saved.append(dest)
        browser.close()
    return saved


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE / "screenshots"))
    ap.add_argument("--no-create-entry", action="store_true")
    args = ap.parse_args()
    token = load_secrets()["HA_TOKEN"]
    ok = True

    import time
    deadline = time.time() + 300
    while True:
        try:
            st, cfg = api("GET", "/api/config", token)
        except OSError:
            st, cfg = 0, None
        if isinstance(cfg, dict) and cfg.get("state") == "RUNNING":
            break
        if time.time() > deadline:
            print("Home Assistant did not reach state RUNNING within 5 minutes")
            return 1
        time.sleep(3)
    print(f"GET /api/config -> HTTP {st}; version {cfg.get('version') if isinstance(cfg, dict) else '?'}")
    comps = cfg.get("components", []) if isinstance(cfg, dict) else []
    print(f"'{DOMAIN}' in loaded components: {DOMAIN in comps}")

    st, entries = api("GET", f"/api/config/config_entries/entry?domain={DOMAIN}", token)
    entries = entries if isinstance(entries, list) else []
    print(f"GET /api/config/config_entries/entry?domain={DOMAIN} -> HTTP {st}; {len(entries)} entr(y/ies)")

    if not entries and not args.no_create_entry:
        st, flow = api("POST", "/api/config/config_entries/flow", token, {"handler": DOMAIN})
        print(f"POST /api/config/config_entries/flow handler={DOMAIN} -> HTTP {st}; "
              f"result type: {flow.get('type') if isinstance(flow, dict) else flow}")
        if isinstance(flow, dict) and flow.get("type") == "form" and not flow.get("data_schema"):
            # One-click form with no fields: submit it empty.
            st, flow = api("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", token, {})
            print(f"POST /api/config/config_entries/flow/<id> (empty submit) -> HTTP {st}; "
                  f"result type: {flow.get('type') if isinstance(flow, dict) else flow}")
        if isinstance(flow, dict) and flow.get("type") == "form":
            print(f"  flow needs input (step '{flow.get('step_id')}'); finish it in the UI. Aborting flow.")
            api("DELETE", f"/api/config/config_entries/flow/{flow['flow_id']}", token)
        st, entries = api("GET", f"/api/config/config_entries/entry?domain={DOMAIN}", token)
        entries = entries if isinstance(entries, list) else []
        print(f"after flow: {len(entries)} entr(y/ies)")

    for e in entries:
        print(f"  entry '{e.get('title')}' state={e.get('state')} reason={e.get('reason')}")
        if e.get("state") != "loaded":
            ok = False

    res = asyncio.run(ws_calls(token, [{"type": "get_panels"}, {"type": "get_states"}]))
    panels = res[0].get("result", {}) or {}
    ours = {k: v for k, v in panels.items()
            if DOMAIN in k or DOMAIN in json.dumps(v.get("config") or {}) or "access" in k}
    print(f"WS get_panels -> {len(panels)} panels; access_profile-related: {sorted(ours) or 'none'}")
    states = [s["entity_id"] for s in (res[1].get("result") or [])
              if DOMAIN in s["entity_id"] or DOMAIN in json.dumps(s.get("attributes", {}))]
    print(f"WS get_states -> access_profile-related entities: {states or 'none'}")

    if not (DOMAIN in comps or entries or ours):
        print("RESULT: access_profile did NOT load (not in components, no entry, no panel).")
        ok = False

    pages = [("01-overview", "/lovelace/0"),
             ("02-integration-page", f"/config/integrations/integration/{DOMAIN}")]
    for i, url_path in enumerate(sorted(ours), start=3):
        pages.append((f"{i:02d}-panel-{url_path}", f"/{url_path}"))
    screenshot(token, pages, Path(args.out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
