# ap-testbed: throwaway Home Assistant for the Access profile UI

Local-only Home Assistant `2026.11.2` (pinned) in Docker, used to run our own
`access_profile` mockup integration. No HACS, no third-party integrations.

- URL: http://127.0.0.1:8124 (bound to localhost only)
- Container: `ap-testbed`, not privileged, bridge network (no host networking)
- Credentials: `testbed\.secrets.env` (username, random password, long-lived token).
  Local only; do not share or commit.

## Files
| File | What it does |
|---|---|
| `compose.yaml` | Service definition, `config/` plus the two read-only UI mounts |
| `compose.noui.yaml` | Override `start.ps1` uses only when `..\ui` is missing |
| `start.ps1` | Starts the container and waits for HTTP. `-Recreate` forces a fresh container |
| `stop.ps1` | Stops the container (keeps `config/`) |
| `onboard.py` | Finishes onboarding through the HTTP API, writes `.secrets.env` |
| `check-ui.ps1` / `check_ui.py` | Recreates with UI mounts, checks the integration loads, takes screenshots |
| `screenshots/` | Headless Playwright Chromium screenshots |
| `.venv/` | Python venv with Playwright and websockets |

## Mounts (contract with the UI agent)
- `..\ui\custom_components\access_profile` -> `/config/custom_components/access_profile` (ro)
- `..\ui\data` -> `/config/access_profile` (ro); the integration reads `profiles.json` from it

## Start / stop
```powershell
cd C:\Users\Josh\ghsa-triage\_ideas\01-hacs-security-score\testbed
.\start.ps1
.\stop.ps1
```
First run on an empty `config/` only: `.\.venv\Scripts\python.exe -I onboard.py`

## After changing the UI integration
```powershell
.\check-ui.ps1
```
This recreates the container (picks up Python changes), prints `access_profile` log lines and any
errors, creates the config entry if missing, checks the panel via the WebSocket API, and saves
screenshots to `screenshots\`. The browser is Playwright's bundled Chromium, headless. Never
use Microsoft Edge here. For JS-only changes, bump `VERSION` in `__init__.py` or hard-reload.

## Tear down
```powershell
docker compose -f compose.yaml -f compose.noui.yaml down
Remove-Item -Recurse -Force .\config, .\.secrets.env
```
Optional: `Remove-Item -Recurse -Force .\.venv, .\screenshots` and
`docker image rm ghcr.io/home-assistant/home-assistant:2026.11.2`.
