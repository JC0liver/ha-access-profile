# Fresh 100 (holdout), 2026-11-19

## Method

- **Sample:** 100 integrations drawn at random (`random.seed(20261120)`) from the 5,293 catalog integrations not used before (no overlap with the first 10 or the tuning 100). The list is in `sample.tsv`.
- **Clones:** shallow clones at the `last_version` tag, or the default branch for the 2 repos with no release, in `untrusted/repos100b/`. I verified each clone's tag against the sample. Nothing was run or installed.
- **Rules:** the v2 rules from the tuning run, used **unchanged**, so this is the honest noise number. Every High access and Needs review hit was checked by hand.
- **Miss check:** I grepped the 80 Standard repos for risky patterns, including download-and-run (`chmod`, `S_IEXEC`, `0o7xx`, `write_bytes`). There were no hits, and the grep does catch the known `chmod` in WebRTC. Not proof of no misses.

## Result

80 Standard, 11 Extended, 6 High access, 3 Needs review.

| Repo | Scanner level | Hand verdict | Right level |
|---|---|---|---|
| advanced_snapshot | Needs review | False positive: committed `__pycache__/*.pyc`, timestamp-based (flags 0), so Python ignores them once the source changes | Standard |
| dell-fans-ipmi-ha | Needs review | `.pyc` false positive as above. TLS off to a LAN iDRAC is accurate | High access |
| microair-easytouch-cloud | Needs review | False positive: the RFC 5054 SRP prime as a hex string matched the base64 check | Standard |
| **AlexxIT WebRTC** | High access | **Under-rated.** It downloads the go2rtc binary from the author's GitHub releases at runtime (`utils.py:88-108`), marks it executable and runs it, with no hash check. Its unauthenticated views use signed requests, link tokens or a session cookie (by design) | Needs review |
| neonplan3d | High access | False positive: the unauthenticated view serves only static frontend files | Extended |
| f1_sensor | High access | Accurate, by design: OAuth callback | High access |
| Aqara-LANLink | High access | Accurate: TLS off to a self-signed LAN hub, ffmpeg from a command constant | High access |
| azimut-energy | High access | Accurate: MQTT TLS off to a broker found by zeroconf on the LAN | High access |
| zte_tracker | High access | Accurate: router on the LAN | High access |

**Holdout noise:**
- 5 of the 9 High/Review levels are wrong.
- All 3 Needs review results were false positives again.
- 1 real download-and-run case was rated one level too low.
- 1 of 6 High access results was a false positive (static frontend files, the same pattern as orphan-cleaner in the tuning run).
- The 80 Standard and 11 Extended weren't hand-checked beyond the miss grep.

## Proposed v3 fixes (not applied, to keep this sample a fair test)

1. **`.pyc`:** flag only unchecked hash-based `.pyc` files (flags = 3), which Python loads without checking the source. Timestamp-based caches become an "accidental files" note.
2. **Hex strings:** skip pure hex strings in the base64 obfuscation check.
3. **Download-and-run:** new Needs review check for a file that is made executable (`os.chmod` with `S_IEXEC` or `0o7xx`) or written then executed. This would catch WebRTC.
4. **Static files:** an unauthenticated view that only returns `FileResponse` from a fixed folder, or loader JS, becomes Extended ("serves static files without login").

After v3 these would need another fresh sample to measure.
