# 100-integration run, 2026-11-19

## Sample and method

- **Sample:** 100 integrations drawn at random (`random.seed(20261119)`) from the 5,393 integrations in the HACS catalog (`data-v2.hacs.xyz/integration/data.json`), excluding hacs/integration and the first 10. The list is in `sample.tsv`.
- **Clones:** shallow clones at each repo's `last_version` tag, in `untrusted/repos100/`. All 100 cloned and all 100 had `custom_components/`. Nothing was run or installed.
- **Scan:** `scan.py`, with levels from `levels.py` via `summarise.py`. Every High access and Needs review hit was then checked by hand.
- **Miss check:** the 70 Standard repos were grepped for patterns the scanner might miss (`shell=True`, `exec(`, `eval(`, pickle, `yaml.load(`, TLS off in dict form, `requires_auth = False`, `urlretrieve`, `spec_from_file`). There were no hits. The five near-misses (custom `ssl=`/`verify=` contexts) all load a pinned CA. This is a grep, not proof of no misses.

## v1 rules (as in the proposal)

70 Standard, 4 Extended, 23 High access, 3 Needs review. Results: `scan-results-v1.json`.

### Hand check of the 26 High / Needs review repos

| Verdict | Repos | Why |
|---|---|---|
| Real weakness | 1 | pippyn/Afvalbeheer: `requests.get(..., verify=False)` to a fixed internet waste-calendar API (`collectors/shared/klikogroep.py:47`) |
| Accurate, low concern | 3 | ecodevices, speedport-smart, rutos: TLS verification off for a LAN device (router or meter with a self-signed cert) |
| Accurate, by design | 16 | Bundled dashboard card loaded from a local path (13 repos), runs ffmpeg/ffprobe (pipeless, yi-hack), HLS view on a capability token (JellyHA) |
| False positive (wrong level) | 6 | maintenance_supporter (`.bin` zlib data files, long data lines), Afvalbeheer (inline SVG data URI flagged as obfuscation; real level is High, not Review), zwift (generated protobuf `_pb2.py`), afvalcontainer (`verify=False` only in shipped `tests/`), homewizard-realtime (`check_hostname = False` with a pinned CA and `CERT_REQUIRED`), orphan-cleaner (unauthenticated views serve only static panel HTML/JS) |

Two more false positives didn't change a level: photoprism and JellyHA mark views `requires_auth = False` but check the login inside the handler.

**v1 noise:**
- All 3 Needs review results were false positives.
- 16 of 23 High access repos were routine (mostly a bundled card), which would put 1 in 4 integrations at High access.

## v2 rule changes (in `scan.py`, `levels.py`; v1 kept as `scan_v1.py`)

1. **Dashboard JS:** loading the integration's own JS from a local path is now Extended ("Adds its own card or panel JavaScript"). High access is only for remote, `http(s)://` or `data:` scripts.
2. **Self-checking views:** an unauthenticated view whose handler checks `KEY_AUTHENTICATED`, `hass_user` or `hass_refresh_token_id` is Extended ("checks the login in their own code").
3. **Fixed programs:** a subprocess with a literal argument list starting with a program name and no shell is Extended. A variable command or `shell=True` stays High access.
4. **TLS with a pinned CA or PSK:** `check_hostname = False` is not flagged when the file sets `CERT_REQUIRED`.
5. **Tests skipped:** `tests/`, `test/` and `test_*.py` inside the integration are skipped, since HA never loads them.
6. **Obfuscation noise removed:** the "line over 2000 chars" rule is gone. Base64 literals that start like PNG, JPEG, GIF, SVG or WebP are ignored. `.bin` no longer counts as a binary; executable formats and archives still do.

## v2 result

73 Standard, 18 Extended, 9 High access, 0 Needs review. Results: `scan-results.json`. On the first 10, v2 gives the same levels as v1 (dreame-vacuum still Needs review).

| Remaining High access | Verdict |
|---|---|
| Afvalbeheer | real weakness (TLS off to an internet API) |
| ecodevices, speedport-smart, rutos | accurate, LAN TLS off |
| pipeless, yi-hack, photoprism | accurate, run ffmpeg-type programs from a built command |
| JellyHA | accurate, token-based unauthenticated HLS view |
| orphan-cleaner | false positive (static panel files) |

**v2 noise:** 1 of 9 High access levels is wrong, and no Needs review results are wrong.

**Caveats:**
- The rules were tuned on this same sample, so the next random 100 is the honest test.
- Rule 1 opens a gap: local JS isn't inspected, and it could itself fetch remote code.
- Rule 3 trusts the program name (e.g. `ffmpeg`), not its arguments.
