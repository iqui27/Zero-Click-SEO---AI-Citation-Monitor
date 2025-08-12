# Smoke tests & validation checklist

This repository includes an automated smoke test that verifies the deployment is healthy and can run a full job end-to-end.

What it validates
- Homepage: 200 OK and contains <title>SEO Analyzer</title>
- Health: GET /api/health returns {"status":"ok"}
- Job lifecycle: Start a new run and poll SSE at /api/runs/{id}/stream until completion

How to run locally
- Default target is https://zero-click.iqui27.codes
- Run: scripts/smoke.sh
- Or directly: python3 scripts/smoke_test.py

Configuration (env vars)
- BASE_URL (default: https://zero-click.iqui27.codes)
- HEALTH_PATH (default: /api/health)
- START_PATH (default: /api/runs)
- START_METHOD (default: POST)
- START_BODY (default: {})
- STREAM_PATH_TEMPLATE (default: /api/runs/{id}/stream)
- AUTH_BEARER (optional)
- EXTRA_HEADERS (optional JSON, applied to all requests)
- TIMEOUT_SECS (default: 15)
- STREAM_TIMEOUT_SECS (default: 300)

Exit codes (CI visibility)
- 0 success
- 2 homepage check failed (status/content)
- 3 health check failed
- 4 start job failed
- 5 stream failed or timed out
- 6 unexpected error

CI usage examples
- GitHub Actions step:
  - name: Smoke tests
    run: |
      chmod +x scripts/smoke.sh
      scripts/smoke.sh

Validation checklist (manual if needed)
- [ ] Homepage loads with expected title
- [ ] /api/health -> {"status":"ok"}
- [ ] Starting a job returns an id
- [ ] SSE stream emits completion event/marker
- [ ] Script exits 0
