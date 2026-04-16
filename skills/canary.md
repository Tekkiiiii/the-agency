---
name: canary
description: >
  Post-deploy canary monitoring loop — runs continuous health checks against
  a canary deployment, compares metrics against baseline, alerts on deviation,
  and optionally rolls back. Triggers when: after a staged rollout (land-and-
  deploy or railway-deploy), during any canary phase, or when manually
  monitoring a deploy in real time. Key capability: adaptive baselines that
  learn from traffic patterns, not static thresholds. Also for: A/B test
  analysis, incident detection, and performance regression monitoring.
---

# /canary — Canary Deployment Monitor

Continuous health monitoring with automatic rollback on signal.

## When to Activate

Trigger `/canary` when:
- After staged rollout begins
- During canary phase of land-and-deploy
- Monitoring a real-time deploy
- A/B test monitoring
- Performance regression detection

## Canary States

```
┌─────────────────────────────────────────────────────────────┐
│  CANARY STATES                                             │
├───────────┬─────────────────────────────────────────────────┤
│ IDLE      │ No canary running                               │
│ PHASE_1   │ 5% traffic — initial validation                 │
│ PHASE_2   │ 25% traffic — stability confirmation            │
│ PHASE_3   │ 100% traffic — full promotion                   │
│ ROLLBACK  │ Reverting to previous version                   │
│ PROMOTED  │ Canary fully promoted, monitoring continues     │
└───────────┴─────────────────────────────────────────────────┘
```

## Preamble

```
/canary {deployment-url} {baseline-url}
```

**Run at start:**
```bash
# Verify canary is reachable
curl -sf "{canary-url}/health" && echo "CANARY HEALTHY" || echo "CANARY DOWN"

# Get baseline for comparison
curl -sf "{baseline-url}/health" && echo "BASELINE HEALTHY" || echo "BASELINE DOWN"

# Confirm both URLs are different deployments
echo "Canary: {canary-url}"
echo "Baseline: {baseline-url}"
```

## Step 1: Establish Baseline

### Collect baseline metrics

```bash
# Run baseline check — 5 requests, record distribution
for i in {1..5}; do
  TIME=$(curl -sf -o /dev/null -w "%{time_connect}+%{time_starttransfer}+%{time_total}" "https://{baseline-url}/health" 2>/dev/null)
  echo "$TIME"
done

# Record baseline error rate (last 24h or available window)
echo "Baseline errors: {N}/total"
echo "Baseline P99: {N}ms"
echo "Baseline error rate: {N}%"
```

### Store baseline

```
BASELINE — {timestamp}
════════════════════════════════
URL:           {baseline-url}
P50 latency:   {N}ms
P99 latency:   {N}ms
Error rate:    {N}%
Status codes:  200={N}, 4xx={N}, 5xx={N}
Health:        OK
```

## Step 2: Phase 1 — 5% Traffic Monitor

**Duration: 5 minutes**

```bash
# Start monitoring loop
echo "PHASE 1: 5% traffic — 5 minutes"
echo "Checking every 30 seconds..."

for i in {1..10}; do
  # Health check
  STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "https://{canary-url}/health" 2>/dev/null || echo "000")

  # Latency sample
  LATENCY=$(curl -sf -o /dev/null -w "%{time_total}" "https://{canary-url}/api/health" 2>/dev/null || echo "999")

  # Error rate
  ERRORS=$(curl -sf "https://{canary-url}/api/errors/count" 2>/dev/null || echo "0")

  echo "$(date '+%H:%M:%S') | status=$STATUS | latency=${LATENCY}s | errors=$ERRORS"

  # Alert thresholds
  if [ "$STATUS" != "200" ]; then
    echo "ALERT: Non-200 status: $STATUS"
  fi
  if [ "$(echo "$LATENCY > 2" | bc)" = "1" ]; then
    echo "ALERT: Latency > 2s: ${LATENCY}s"
  fi

  sleep 30
done

echo "PHASE 1 COMPLETE"
```

### Phase 1 Gate

```
PHASE 1 GATE — {version}
════════════════════════════════
Health check:  {N}/10 passed
P99 latency:    {N}ms (threshold: {N}ms)
Errors:        {N} (threshold: {N})
Status:        PASS | FAIL

→ PASS: proceed to Phase 2
→ FAIL: trigger rollback
```

## Step 3: Phase 2 — 25% Traffic Monitor

**Duration: 10 minutes**

```bash
echo "PHASE 2: 25% traffic — 10 minutes"
echo "Checking every 30 seconds..."

# More comprehensive checks
for i in {1..20}; do
  # Multi-endpoint health
  for ENDPOINT in /health /api/health /api/ping; do
    STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "https://{canary-url}${ENDPOINT}" 2>/dev/null || echo "000")
    if [ "$STATUS" != "200" ]; then
      echo "ALERT [$(date '+%H:%M:%S')]: $ENDPOINT → $STATUS"
    fi
  done

  # Latency comparison vs baseline
  CANARY_LATENCY=$(curl -sf -o /dev/null -w "%{time_total}" "https://{canary-url}/health" 2>/dev/null)
  BASELINE_LATENCY=$(curl -sf -o /dev/null -w "%{time_total}" "https://{baseline-url}/health" 2>/dev/null)

  RATIO=$(echo "scale=2; $CANARY_LATENCY / $BASELINE_LATENCY" | bc 2>/dev/null || echo "0")

  if [ "$(echo "$RATIO > 1.5" | bc)" = "1" ]; then
    echo "ALERT: Canary ${RATIO}x slower than baseline (${CANARY_LATENCY}s vs ${BASELINE_LATENCY}s)"
  fi

  sleep 30
done

echo "PHASE 2 COMPLETE"
```

### Phase 2 Gate

```
PHASE 2 GATE — {version}
════════════════════════════════
Health check:  {N}/20 passed
Latency ratio: {N}x baseline (threshold: <1.5x)
Error rate:    {N}% (baseline: {N}%)
P99 latency:   {N}ms

→ PASS: proceed to Phase 3
→ FAIL: trigger rollback
```

## Step 4: Phase 3 — 100% Promotion

**Duration: 5 minutes post-promotion**

```bash
echo "PHASE 3: Full promotion — 5 minutes post-promotion"

# After traffic shift to 100%
sleep 60  # Let routing stabilize

for i in {1..10}; do
  STATUS=$(curl -sf -o /dev/null -w "%{http_code}" "https://{canary-url}/health" 2>/dev/null || echo "000")
  echo "$(date '+%H:%M:%S') | status=$STATUS"

  if [ "$STATUS" != "200" ]; then
    echo "CRITICAL: Status non-200: $STATUS"
    # Trigger rollback immediately
  fi

  sleep 30
done

echo "PHASE 3 COMPLETE — CANARY PROMOTED"
```

## Step 5: Rollback Trigger

### Trigger on signal

```bash
# Rollback command
rollback_cmd() {
  echo "TRIGGERING ROLLBACK..."
  # Railway
  # railway rollback --deployment @previous

  # Vercel
  # npx vercel alias d_YYYYYYYY.vercel.app production

  # Generic
  # git checkout v{previous-version}
  # Trigger redeploy
}
```

### Rollback criteria

```
ROLLBACK TRIGGER — {version}
════════════════════════════════
Health failures:  {N} consecutive
Error rate:       {N}% (threshold: 5%)
Latency ratio:    {N}x baseline (threshold: 3x)
P99 latency:      {N}ms (threshold: 5000ms)
HTTP errors:      {list of non-200 codes}

Decision: TRIGGER ROLLBACK | CONTINUE | PAUSE
```

## Step 6: Canary Report

```
═══════════════════════════════════════════════════════
CANARY REPORT — {version}
═══════════════════════════════════════════════════════

CANARY:       {canary-url}
BASELINE:     {baseline-url}
VERSION:      {sha}
STARTED:      {ISO}
PROMOTED:     {ISO}

PHASE 1 (5%):
  Duration:   {N} minutes
  Results:    {N}/10 checks passed
  Alerts:     {N}

PHASE 2 (25%):
  Duration:   {N} minutes
  Results:    {N}/20 checks passed
  Alerts:     {N}

PHASE 3 (100%):
  Duration:   {N} minutes
  Results:    {N}/10 checks passed
  Alerts:     {N}

FINAL STATE:
  Status:         PROMOTED | ROLLED BACK | PAUSED
  Final latency:  {N}ms
  Final errors:   {N}

ROLLBACK EVENTS: {N}

REPORT GENERATED: {ISO}
```

## Canary Modes

### Passive monitoring (default)

Run checks at regular intervals. Alert but don't auto-rollback without confirmation.

### Active mode (aggressive)

```
/canary {url} --mode=active --rollback-on=health,latency,error-rate
```

Auto-rollback on any threshold breach. Use only when rollback is fast and safe.

### A/B test mode

```
/canary {url-a} {url-b} --mode=ab --compare=conversion,latency,error-rate
```

Compare two variants. Report which wins.

## Adaptive Baselines

```
ADAPTIVE BASELINE — {version}
════════════════════════════════

Collects baseline from:
1. Pre-deploy metrics (last 24h)
2. Current production baseline
3. Synthetic baseline from same deploy

Baseline drift:
  If baseline error rate > 5%, re-anchor baseline
  If baseline latency changes > 50%, alert

This prevents:
  - Baseline being too loose (miss real issues)
  - Baseline being too tight (false positives on deploys)
```

## Important Rules

- **Health check beats latency check.** If the health endpoint is up, the deploy is working.
- **Baseline is the truth.** Don't compare against hope — compare against what's running now.
- **Rollback is not failure.** A triggered rollback is the canary system working.
- **Document every alert.** Alert → investigation → resolution → lesson.
- **Adaptive baselines prevent drift.** Re-anchor when production itself changes.