"""One-off: exercise the panel filters in the testbed and screenshot. Bundled Chromium only."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from check_ui import BASE, load_secrets
from playwright.sync_api import sync_playwright

token = load_secrets()["HA_TOKEN"]
tokens = {"hassUrl": BASE, "clientId": f"{BASE}/", "access_token": token, "token_type": "Bearer",
          "expires_in": 315360000, "refresh_token": "", "expires": 4102444800000}
out = Path(__file__).resolve().parent
errors = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1400, "height": 1000})
    ctx.add_init_script("try{localStorage.setItem('hassTokens', %s);}catch(e){}" % json.dumps(json.dumps(tokens)))
    pg = ctx.new_page()
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(BASE + "/access-profile", wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(3000)
    pg.locator("#f-sample").select_option("run100c")
    pg.wait_for_timeout(500)
    pg.locator("button[data-flevel='high']").click()
    pg.wait_for_timeout(500)
    pg.locator("#f-sample").scroll_into_view_if_needed()
    pg.screenshot(path=str(out / "04-filter-holdout2-high.png"))
    print("cards shown:", pg.locator("#cards .card").count(), "| heading:", pg.locator("#cards h2").inner_text())
    pg.locator("button[data-flevel='high']").click()
    pg.locator("#f-sample").select_option("all")
    pg.locator("#f-q").fill("webrtc")
    pg.wait_for_timeout(500)
    print("search 'webrtc':", pg.locator("#cards h2").inner_text())
    pg.locator("#cards button.btn[data-repo]").first.click()
    pg.wait_for_timeout(500)
    pg.screenshot(path=str(out / "05-dialog-webrtc.png"))
    b.close()
print("console errors:", errors or "none")
