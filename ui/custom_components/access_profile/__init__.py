"""Access profile mockup: a sidebar panel showing per-integration access levels.

Read-only: it serves its own frontend file and reads
/config/access_profile/profiles.json. It writes nothing to disk.
Set up via the UI (Add integration > Access profile) or `access_profile:` in YAML.
"""

from __future__ import annotations

import json
from pathlib import Path

from aiohttp import web

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

DOMAIN = "access_profile"
PANEL_URL = "access-profile"
STATIC_URL = "/access_profile_static"
JS_FILE = "access-profile-panel.js"
SIGNAL_JS = "marketplace-signal.js"
VERSION = "0.2.2"  # cache-buster for the JS modules

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)


class ProfilesView(HomeAssistantView):
    """GET /api/access_profile/profiles: the JSON from the data folder (auth required)."""

    url = "/api/access_profile/profiles"
    name = "api:access_profile:profiles"

    def __init__(self, path: Path) -> None:
        self._path = path

    async def get(self, request: web.Request) -> web.Response:
        hass = request.app["hass"]
        try:
            text = await hass.async_add_executor_job(self._path.read_text, "utf-8")
            data = json.loads(text)
        except (OSError, ValueError) as err:
            return self.json_message(f"Cannot read {self._path.name}: {err}", 404)
        return self.json(data)


async def _async_register(hass: HomeAssistant) -> None:
    state = hass.data.setdefault(DOMAIN, {"routes": False, "panel": False})
    if not state["routes"]:  # HTTP routes can only be added once per run
        state["routes"] = True
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "frontend"), False)]
        )
        hass.http.register_view(
            ProfilesView(Path(hass.config.path("access_profile", "profiles.json")))
        )
        # Show the Access profile inside the Marketplace repository page
        frontend.add_extra_js_url(hass, f"{STATIC_URL}/{SIGNAL_JS}?v={VERSION}")
    if state["panel"]:
        return
    state["panel"] = True
    # The overview panel stays reachable at /access-profile but is no longer in the sidebar
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL,
        webcomponent_name="access-profile-panel",
        sidebar_title=None,
        sidebar_icon=None,
        module_url=f"{STATIC_URL}/{JS_FILE}?v={VERSION}",
        require_admin=False,
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    if DOMAIN in config:
        await _async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await _async_register(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Static path and view can't be unregistered; removing the panel is enough.
    frontend.async_remove_panel(hass, PANEL_URL)
    hass.data[DOMAIN]["panel"] = False
    return True
