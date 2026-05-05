# NEXT ACTION — direct chat reliability

**Session:** `agent-workspace-mobile-streaming-2026-05-04`
**Resume command:** `python scripts/ai_runner.py resume`

## Completed
- Direct chat now uses bounded per-provider timeouts instead of waiting on a single unhealthy backend indefinitely
- Direct chat now retries recovery without keeping a broken model pin and can fall through to the next healthy provider chain
- When recovery still fails, chat now returns a stable in-thread diagnostic instead of surfacing a raw 502/503 error bubble
- Added regression coverage for direct-chat recovery and provider timeout plumbing
- Re-ran `pytest -x` successfully (`757 passed, 15 skipped`)

## Next
- Review the patch diff for any polish opportunities
- Commit the direct-chat reliability fix
- Push the branch and open a PR targeting `master`
