# Fresh 100 (holdout for v3), 2026-11-19

## Method

- **Sample:** 100 integrations drawn at random (`random.seed(20261121)`) from the 5,193 catalog integrations not used in any earlier sample. The list is in `sample.tsv`.
- **Clones:** shallow clones at the `last_version` tag, or the default branch if there is no release, in `untrusted/repos100c/`. Nothing was run or installed.
- **Rules:** v3 (`scan.py`, `levels.py`; previous versions kept as `scan_v1.py` and `scan_v2.py`), used unchanged on this sample. Every High access and Needs review hit was checked by hand.
- **Miss check:** I grepped the 79 Standard repos for risky patterns, including download-and-run and `b64decode`. The only hits were 4 ordinary base64 data decodes (JWT payloads, keys). Not proof of no misses.

## v3 changes (made after the run100b holdout)

1. **`.pyc`:** only unchecked hash-based files (flags 3) count as a binary. Timestamp caches are noted, not levelled.
2. **Hex strings:** pure hex strings are no longer treated as base64.
3. **Download-and-run:** new Needs review check, `make_executable`. It fires on `chmod` with an execute bit, in a file that also downloads, on a target not named like a directory. The directory exclusion came from a `chmod 0o700` on a private folder in run100b (zte_tracker).
4. **Static files:** an unauthenticated GET-only view that returns files and reads no request input is Extended ("Serves static files without login").

**Re-check of earlier samples with v3:**
- First 10: unchanged.
- run100: 73 / 19 / 8 / 0. orphan-cleaner is now Extended.
- run100b: 82 / 12 / 5 / 1. Its 3 false-positive Needs review are fixed, neonplan3d is Extended, and WebRTC is Needs review.
- These two samples influenced the rules, so they don't count as tests.

## Result on the fresh 100

79 Standard, 12 Extended, 9 High access, 0 Needs review.

| Repo | Hand verdict |
|---|---|
| **recalbox** | Accurate, real weaknesses. `ping` runs through `create_subprocess_shell` with the configured host in an f-string (`api.py:403-406`); the host comes only from the admin's config flow. An unauthenticated POST endpoint updates entity state for anyone who can reach HA (`rest_controllers/rest_controller.py:14`). TLS verification is also off. |
| **mcp-assist** | Accurate, real weakness. It always uses `CERT_NONE` when SSL is on, and sends a bearer token over it (`openclaw_client.py:266-269`) |
| ikuai, synology-srm-router, Ksenia Lares, niko-home-control-local | Accurate, low concern: TLS off to a LAN router, alarm panel or controller |
| esphome-intercom | Accurate, by design: runs ffmpeg from a built command |
| auckland_transport | False positive: unauthenticated view serves an allowlist of card JS files (reads `match_info`, so the static rule didn't apply) |
| prezero-bielsko | False positive: unauthenticated view returns a generated icon SVG; the `color` query is sanitised to `#RRGGBB` |

## Noise across the samples (each one tested on rules it didn't shape)

| Run | Rules | High/Review results | Wrong by hand |
|---|---|---|---|
| run100b | v2 | 9 | 5 (all 3 Needs review false, 1 under-rated) |
| run100c | v3 | 9 | 2 (both static-content views), 0 Needs review false, no misses found |

**Remaining gaps:**
- Unauthenticated views that serve allowlisted or generated static content still read as High access.
- Needs review fired 0 times on this sample, so its accuracy on fresh data is untested. Its only true positives so far (dreame-vacuum, WebRTC) both come from samples used to shape the rules.
