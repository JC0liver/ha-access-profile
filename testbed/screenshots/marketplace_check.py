"""One-off: check the Access profile line on Marketplace repository pages. Bundled Chromium only."""
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
    ctx = b.new_context(viewport={"width": 1400, "height": 1100})
    ctx.add_init_script("try{localStorage.setItem('hassTokens', %s);}catch(e){}" % json.dumps(json.dumps(tokens)))
    pg = ctx.new_page()
    pg.on("console", lambda m: errors.append(m.text) if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    for name, rid in (("dreame", "544426802"), ("webrtc", "356778495")):
        pg.goto(f"{BASE}/marketplace/repository/{rid}", wait_until="networkidle", timeout=90000)
        try:
            pg.locator("li.ap-signal").wait_for(timeout=30000)
        except Exception as e:
            print(name, "no ap-signal:", e.__class__.__name__)
            pg.screenshot(path=str(out / f"06-mkt-{name}-missing.png"))
            continue
        print(name, "signal:", pg.locator("li.ap-signal").inner_text().strip().replace("\n", " "))
        pg.locator("ha-card.details").scroll_into_view_if_needed()
        pg.screenshot(path=str(out / f"06-mkt-{name}.png"))
        print(name, "before click: details visible:", pg.locator("li.ap-details").is_visible())
        pg.locator("li.ap-signal").click()
        pg.wait_for_timeout(400)
        print(name, "expanded:", pg.locator("li.ap-signal").get_attribute("aria-expanded"),
              "| details visible:", pg.locator("li.ap-details").is_visible())
        pg.locator("ha-card.details").scroll_into_view_if_needed()
        pg.screenshot(path=str(out / f"07-mkt-{name}-expanded.png"))
    b.close()
print("console errors/warnings:", errors or "none")
