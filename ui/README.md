# Access profile UI mockup

A mockup for the Security group, not production code. It shows what the "Access profile" label from
`../proposal.md` section 5 could look like inside Home Assistant. The data is the real prototype scan of 10 HACS
integrations (`../prototype/scan-results.json`).

## Files

| Path | What it is |
|---|---|
| `../prototype/levels.py` | Stdlib only. Turns `scan-results.json` into `data/profiles.json` using the proposal's level table, and refreshes the inlined copy in `preview.html`. Prints the level for each repo and flags any that differ from the proposal's sample. Run: `python -I levels.py` from `prototype/`. |
| `data/profiles.json` | Generated. For each integration: repo, name, domain, version (from the manifest), release tag, level, reasons (grouped by check, with counts and up to 3 `file:line` GitHub links at the tag), hosts, and `author_note`. The two author notes (pyscript, hass-oidc-auth) are marked `"sample": true`: **we wrote that text, not the authors**. |
| `custom_components/access_profile/` | A small custom integration for HA 2026.11.2. It registers the "Access profile" sidebar panel (`panel_custom`), serves `frontend/` at `/access_profile_static` (`async_register_static_paths`), and serves the JSON at `GET /api/access_profile/profiles` (login required). It reads `/config/access_profile/profiles.json` and never writes to disk. |
| `custom_components/access_profile/frontend/access-profile-panel.js` | The panel: a plain web component with no imports and no build step. It shows a legend, a mock HACS / Marketplace repository header (pick any integration) with the chip next to the Download button, one card per integration, and a details dialog with the code links. Chips copy the app "Rating" chip (`ha-assist-chip` filled, `--label-badge-*` colours). All colours come from HA theme variables, so light and dark both work. |
| `preview.html` | Standalone preview. It loads the same JS file as a classic script, with the JSON inlined and a stub `hass` whose `callApi` returns it. It opens from `file://` without HA and has light/dark and narrow toggles. |

## How the test system mounts it

- `ui\custom_components\access_profile` → `/config/custom_components/access_profile` (read-only)
- `ui\data` → `/config/access_profile` (read-only)
- Instance: `http://127.0.0.1:8124`

To turn it on, do either of these:
- UI: Settings > Devices & services > Add integration > "Access profile (mockup)", then confirm (single instance).
- YAML: add a line `access_profile:` to `configuration.yaml` and restart.

"Access profile" then shows in the sidebar for all users. After you edit the JS, bump `VERSION` in `__init__.py` (it is a
cache-buster in the module URL), or hard-refresh the browser.

## Notes

- Release tags and display names are typed into `levels.py` from the HACS catalog (`last_version`, `manifest_name`).
  Download counts come from proposal section 7. Nothing is fetched.
- Some manifests carry a placeholder version (`0.0.0`, `v0.0.0`), which release workflows usually overwrite. When the
  version and the tag differ, the UI shows both.
- Hard-coded hosts are listed under "Contacts" but never set the level (decided 2026-11-19). Extended is blue.
