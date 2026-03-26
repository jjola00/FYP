# LINE CAPTCHA Implementation Assessment

**Date:** 2026-01-30
**Based on:** FYP research docs, line-research.txt, fyp-additions.txt, and codebase review

---

## Current State Summary

The implementation is well-structured and already incorporates many MTD principles from the research:

| MTD Principle | Implementation Status |
|--------------|----------------------|
| Per-session procedural generation | Done - Bezier paths with seeded RNG, 6 path families |
| Short TTL | Done - 10s |
| Per-challenge tolerance jitter | Done - +/-2px mouse, +/-3px touch |
| Peek rate limiting | Done - 100ms min interval, 120 max peeks, progressive decay |
| Monotonic progress enforcement | Done - Backtrack limited to 10px |
| Behavioral analysis (11-check) | Done - Speed, accel, regularity, curvature, ballistic, hesitation, etc. |

---

## A. Bot Security Improvements

### A1. Curvature-Behavior Coupling (IMPLEMENTED)

**Research reference** (fyp-additions.txt):
> "Curvature-behavior coupling is a second-order signal aimed at intent"

**Current state** (`main.py:442-488`):
The curvature check exists but has weak thresholds:
- `CURVATURE_SLOWDOWN_RATIO_MIN = 1.04` (only 4% slowdown expected)
- Check is often inconclusive when `curvature_contrast_rad < 0.08`

**Problem:**
Paths with gentle curves don't trigger meaningful curvature contrast, making the check inconclusive for many challenges.

**Status:** Implemented. S-curve and diagonal path families provide sufficient curvature contrast. Curvature check is standalone rejection when applicable, falls back to composite signals otherwise.

**Priority:** Resolved
**Effort:** Done

---

### A2. "Slow Careful Bot" Vulnerability

**Research reference** (fyp-additions.txt):
> "Slow, careful bots (uniform steps, low speed) remain the hardest class to block"

**Current bot bypass command:**
```bash
python scripts/bot_sim.py --step-ms=20 --step-ms-jitter=0.15 --curvature-aware --curvature-slow-factor=1.2
```

**Current gap:**
The `regularity_flag` only triggers when BOTH `dt_cv < 0.08` AND `dd_cv < 0.08`. A bot with modest timing jitter passes.

**Potential improvements:**

1. **Micro-acceleration patterns** — IMPLEMENTED as `ballistic_profile` check. Measures speed across first/mid/last thirds; flat profile triggers flag.

2. **Hesitation detection** — IMPLEMENTED as `hesitation` check. Counts micro-pauses at high-curvature regions; absence of hesitation is suspicious.

3. **Jitter frequency analysis** — NOT IMPLEMENTED. Deferred; current 11-check system achieves 100% bot rejection without spectral analysis.

**Priority:** Resolved (items 1-2 implemented, item 3 deferred)
**Effort:** Done

---

### A3. Peek Oracle Remains Exploitable

**Research reference** (line-research.txt):
> "The peek endpoint reveals future path segments on demand, acting as an oracle"

**Current mitigation** (`main.py:175-194`):
Distance constraint returns empty `ahead` if cursor too far from path.

**Remaining gap:**
A bot at the path can still query 40px ahead repeatedly. The sequential reveal is enforced, but full path is still obtainable segment-by-segment.

**Potential improvements:**

1. **Progressive reveal decay** — IMPLEMENTED. Lookahead distance decays when cursor hasn't advanced sufficiently (`PEEK_DECAY_FACTOR`, `PEEK_DECAY_MIN_ADVANCE_PX`).

2. **Peek-to-progress ratio check** — IMPLEMENTED via peek state enforcement (`ENFORCE_PEEK_STATE`). Tracks max advance speed per second, limits backtracking.

**Priority:** Resolved
**Effort:** Done

---

### A4. Missing Proof-of-Work / Client Binding

**Research reference** (line-research.txt):
> "Obfuscate the API... polymorphic web code generation"

**Current state:**
Token is HMAC-signed but client code is static. A bot can call endpoints directly without running the JS.

**Potential improvements:**

1. **Trajectory hash binding**
   - Client computes hash of trajectory + challenge-specific salt
   - Must accompany verify request
   - [ ] Add `trajectoryHash` field to verify payload

2. **Challenge-specific endpoint tokens**
   - Each challenge gets a unique endpoint suffix or required header
   - Embedded in served HTML/JS
   - [ ] Implement per-challenge API tokens

3. **Timing attestation**
   - Client reports `performance.now()` deltas
   - Server validates against expected browser timing characteristics
   - [ ] Add client timing metadata to requests

**Priority:** Medium
**Effort:** Medium

---

## B. Human Usability Improvements

### B1. TTL vs Path Length Mismatch

**Current config:**
- TTL: 10000ms
- Path: 200-300px
- `TOO_FAST_THRESHOLD_MS`: 1000ms

**Problem:**
Short paths (200px) with careful users might feel rushed. The `min_duration_ms` is calculated as `path_length / max_avg_speed` but `max_avg_speed=800px/s` gives only 250-375ms minimum - not accounting for human reaction time.

**Potential improvements:**
- [ ] Scale TTL dynamically with path length
- [ ] Add 500ms buffer for human "start delay" (time to visually process challenge)
- [ ] Consider path complexity (more curves = more time needed)

**Priority:** Medium
**Effort:** Low

---

### B2. Feedback Messages Are Generic

**Current state** (`app.js:59-91`):
Messages like "Movement looked automated" are frustrating for legitimate users who fail.

**Current messages:**
```javascript
case "behavioural": return "Movement looked automated.";
case "too_perfect": return "Movement looked too perfect.";
case "regularity": return "Movement looked too regular.";
```

**Potential improvements:**
- [ ] "Try moving at a more natural pace" (for `speed_const_flag`)
- [ ] "Vary your speed a bit more" (for `regularity_flag`)
- [ ] "Take your time at the start" (for too-fast initial acceleration)
- [ ] Add visual hints (e.g., pulse the guide line when user strays)

**Priority:** Medium
**Effort:** Low

---

### B3. No Accessibility Considerations

**Gap:**
No mention of motor impairment accommodations. Users with tremors might fail `too_perfect_flag` (paradoxically) or have unusual jitter patterns flagged as bot-like.

**Potential improvements:**

1. **Accessibility mode flag**
   - User opts in via checkbox or detected via browser accessibility settings
   - [ ] Add accessibility toggle to frontend

2. **Relaxed thresholds for accessibility mode**
   - Wider tolerance (30px for mouse)
   - Disabled `too_perfect_flag` and `regularity_flag`
   - Stricter coverage requirements to compensate
   - [ ] Add `accessibilityMode` parameter to verify endpoint

3. **Alternative challenge option**
   - After N failures, offer simpler challenge
   - [ ] Implement fallback challenge flow

**Priority:** Medium
**Effort:** Medium

---

### B4. Touch vs Mouse Parity

**Current config** (`config.py:92-117`):
```python
"mouse": {"tolerance_px": 20, "max_speed_px_per_s": 2000, ...}
"touch": {"tolerance_px": 30, "max_speed_px_per_s": 1800, ...}
```

**Potential issue:**
Touch users on large tablets might have different dynamics than phone users. The 1.1x DPI multiplier may not be sufficient.

**Potential improvements:**
- [ ] Add tablet-specific profile (screen size detection)
- [ ] Scale tolerance with reported screen dimensions
- [ ] Collect more touch data to calibrate thresholds

**Priority:** Low
**Effort:** Medium

---

## C. Architecture / Code Improvements

### C1. Path Variety is Limited

**Current state** (`path.py`):
IMPLEMENTED. 6 path families with weighted random selection.

**MTD principle:**
> "High polymorphism across challenge families"

**Potential improvements:**

All implemented:
- [x] S-curves (double bend with direction reversal)
- [x] Diagonal traversals
- [x] Variable start/end positions (horizontal LR/RL, vertical TB/BT)
- [x] Weighted random selection per challenge via `PATH_FAMILIES`

**Priority:** Resolved
**Effort:** Done

---

### C2. No Challenge Difficulty Progression

**Potential feature:**
After failed attempts, offer easier paths (shorter, straighter) while still maintaining security. This addresses usability without weakening bot defense.

**Implementation ideas:**
- [ ] Track failure count per session
- [ ] After 2 failures, reduce path length to 150-200px
- [ ] After 3 failures, offer accessibility mode prompt
- [ ] Log difficulty level in attempt_logs for analysis

**Priority:** Low
**Effort:** Medium

---

### C3. Logging Enhancements for Research

**Current state:**
Comprehensive `attempt_logs` with 35+ columns - good!

**Potential additions:**
- [ ] Raw peek request log (timestamp, cursor position, response size)
- [ ] Client timing (when did user actually start vs challenge issue time)
- [ ] Path family/variant identifier
- [ ] Curvature profile summary (min, max, mean curvature of path)

**Priority:** Low
**Effort:** Low

---

## Summary: Priority Matrix

| ID | Area | Issue | Impact | Effort | Priority |
|----|------|-------|--------|--------|----------|
| A2 | Security | Slow careful bots pass | High | Medium | **HIGH** |
| A1 | Security | Curvature check often inconclusive | Medium | Low | Medium |
| A3 | Security | Peek oracle exploitable | Medium | Medium | Medium |
| A4 | Security | No client binding/PoW | Medium | Medium | Medium |
| B2 | Usability | Generic failure messages | Medium | Low | Medium |
| B1 | Usability | TTL/path mismatch | Medium | Low | Medium |
| B3 | Usability | No accessibility mode | Medium | Medium | Medium |
| C1 | MTD | Limited path variety | Medium | Low | Medium |
| B4 | Usability | Touch calibration | Low | Medium | Low |
| C2 | Usability | No difficulty progression | Low | Medium | Low |
| C3 | Research | Logging gaps | Low | Low | Low |

---

## Recommended Implementation Order

### Phase 1: Quick Wins (Low effort, good impact)
1. B2 - Improve failure messages
2. C1 - Add path variety
3. A1 - Tune curvature thresholds

### Phase 2: Core Security (Address main vulnerability)
4. A2 - Slow careful bot detection (ballistic profiles, hesitation)
5. A3 - Peek decay / efficiency tracking

### Phase 3: Usability Polish
6. B1 - Dynamic TTL scaling
7. B3 - Accessibility mode

### Phase 4: Advanced Hardening
8. A4 - Client binding / PoW
9. C2 - Difficulty progression

---

## Notes for FYP Evaluation

When testing improvements, remember to:
1. Run ablation tests (disable one check at a time to measure contribution)
2. Collect human baseline data before/after changes
3. Test multiple bot configurations (naive, jittered, curvature-aware, slow)
4. Track false positive rate (humans incorrectly flagged) alongside true positive rate (bots blocked)

Key metrics from your methodology:
- Bot success rate (target: <10%)
- Human success rate (target: >90%)
- Median human solve time (target: <3s)
- User frustration rating (target: <2 on 5-point scale)
