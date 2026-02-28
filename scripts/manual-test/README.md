# WU-34 Manual Validation Harness

This folder provides a guided, repeatable manual test run for Phase 3.1 acceptance.

## Files

- `capture.sh`: Starts `vibecheck-vibe` with terminal transcript capture (`script`).
- `run.sh`: Interactive checklist runner for WU-34 scenarios with pass/fail capture.
- `api.sh`: Session API helper commands (`state`, `wait-pending-approval`, `approve`, etc.).
- `tui_prompts.sh`: Canonical prompt text to paste into the TUI for each scenario.

## Recommended Terminal Layout

- **Terminal A**: TUI runtime + transcript capture  
  `scripts/manual-test/capture.sh --base-url https://<your-domain> --ws-port 7870`
- **Terminal B**: Interactive checklist runner  
  `scripts/manual-test/run.sh --base-url https://<your-domain>`
- **Phone**: Open the same `https://<your-domain>` PWA and connect to the live session.

## Optional Pre-Configuration

You can persist local defaults (ignored by git):

```bash
cat > scripts/manual-test/.env.local <<'EOF'
BASE_URL=https://<your-domain>
PSK=<your-psk>
SID=<optional-live-session-id>
EOF
```

`run.sh` loads this automatically if present.

## Output Artifacts

Each `run.sh` execution writes:

- `artifacts/manual-test/wu34-<timestamp>/report.md`
- `artifacts/manual-test/wu34-<timestamp>/results.tsv`

Share `report.md` back for review/WORKLOG entry.
