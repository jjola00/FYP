# Line CAPTCHA: Implementation Results & Findings

**Project:** Final Year Project - Interactive CAPTCHA with Moving Target Defense
**Date:** February 2026
**Author:** Jay Olajitan

---

## Executive Summary

Designed and implemented a trace-the-path CAPTCHA that achieves **100% bot rejection** while maintaining **high human usability** by detecting unnatural machine precision rather than human errors. The system applies Moving Target Defense (MTD) principles to interaction dynamics, using multi-signal behavioral analysis that requires bots to exhibit human-like imperfection—a fundamentally difficult problem for automated systems.

**Key Result:** Bots fail because they are *too perfect*, not because they are bad at the task.

---

## System Architecture

### Components
| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI (Python) | Challenge generation, verification, behavioral analysis |
| Frontend | Canvas-based JavaScript | Progressive path rendering, trajectory capture, visual feedback |
| Database | SQLite | Challenge state, attempt logging, metrics |

### Core Design Principles
1. **Server-side validation only** - Client is untrusted
2. **Progressive path reveal** - Prevents pre-computation of optimal trajectory
3. **Behavioral analysis** - Detects machine-like patterns in movement
4. **Defense in depth** - Multiple independent detection layers

---

## Moving Target Defense (MTD) Implementation

### Per-Session Randomization
| Element | Variation | Purpose |
|---------|-----------|---------|
| Path shape | 6 families (horizontal, vertical, diagonal, S-curve) | Prevents path memorization |
| Path seed | Cryptographic random | Unique per challenge |
| Tolerance | Per-challenge jitter (±2-3px) | Prevents threshold probing |
| TTL | 8 seconds | Limits computation time |

### Oracle Degradation (Peek System)
| Control | Implementation | Effect |
|---------|----------------|--------|
| Rate limiting | 100ms minimum between peeks | Prevents rapid path extraction |
| Budget limit | 120 peeks maximum | Bounds total information leakage |
| Distance gating | Empty response if cursor off-path | Requires genuine progress |
| Progressive decay | Reduced lookahead without cursor advance | Forces real movement |
| Monotonic progress | Limited backtracking (10px) | Prevents re-peeking |

---

## Behavioral Detection System

### Multi-Signal Approach

The system uses multiple independent signals, requiring **multiple flags** before rejection to minimize false positives for humans:

| Signal | Detection Method | Human Behavior | Bot Behavior |
|--------|------------------|----------------|--------------|
| `too_perfect` | Path deviation analysis | 2-15px natural wobble | <1px precision |
| `regularity` | Coefficient of variation (Δt, Δd) | 8-30% timing variance | <5% machine consistency |
| `speed_const` | Speed variance ratio | 15-40% variation | <8% constant velocity |
| `curvature_adaptation` | Speed at curves vs straights | Slows at curves | Uniform speed |
| `ballistic_profile` | Acceleration pattern | Accel early, decel late | Flat profile |
| `hesitation` | Micro-pause detection | Brief pauses at decisions | No pauses |

### Detection Logic
```
Rejection requires MULTIPLE signals:
- (speed_const AND regularity)
- (accel_flag AND regularity)
- (ballistic_flag AND hesitation_flag)
- too_perfect (alone - strongest signal)
```

### Why This Works
**Humans exhibit natural imperfection:**
- Tremor in hand movement (~8-12Hz)
- Reaction time variations
- Speed adjustment at curves
- Brief hesitations at decision points
- Overcorrection when straying

**Bots exhibit unnatural precision:**
- Mathematically optimal paths
- Uniform timing intervals
- Constant velocity
- No hesitation or correction patterns
- Perfect path adherence

---

## Attacker Model & Testing

### Bot Variants Tested

| Variant | Strategy | Pass Rate | Rejection Reason |
|---------|----------|-----------|------------------|
| Baseline | Direct path following | 0% | too_perfect |
| Timing jitter (15%) | Random timing variation | 0% | too_perfect |
| Spatial jitter (1.5px) | Random position variation | 0% | incomplete |
| Slow step (24ms) | Slower, careful movement | 0% | too_perfect |
| Curvature-aware | Adapts speed to path difficulty | 0% | too_perfect |
| Touch simulation | Emulates touch input | 0% | incomplete |

### Ablation Study Results

Testing with enforcement flags disabled (200 attempts per condition):

| Defense Disabled | Bot Success Rate | Conclusion |
|------------------|------------------|------------|
| All enabled (hardened) | 0% | Full protection |
| `ENFORCE_CURVATURE_ADAPTATION=0` | ~97-100% | **Critical defense** |
| `ENFORCE_REGULARITY=0` | ~15-30% | Important secondary |
| `ENFORCE_BEHAVIOURAL=0` | ~40-60% | Defense in depth |
| `ENFORCE_PEEK_STATE=0` | ~5-10% | Marginal contribution |
| `ENFORCE_SPEED_LIMITS=0` | ~2-5% | Marginal contribution |

**Key Finding:** Curvature-behavior coupling is the dominant defense. Context-dependent validation (behavior relative to task difficulty) is more effective than static thresholds.

---

## Human Usability

### Design Decisions for Usability

| Feature | Implementation | Benefit |
|---------|----------------|---------|
| Generous tolerance | 20-30px depending on input type | Accommodates natural imprecision |
| Coverage-based pass | 75% path coverage required | Brief straying forgiven |
| Visual feedback | Blue/orange/red stroke colors | Real-time guidance |
| Progress indicator | Pulsing finish marker | Encourages completion |
| Helpful messages | "Stay on the line", "Almost there!" | Reduces frustration |

### Tolerance vs Visual Feedback

| Layer | Threshold | User Experience |
|-------|-----------|-----------------|
| Blue stroke | ≤50% of tolerance | "On track" |
| Orange stroke | 50-100% of tolerance | "Near edge - careful" |
| Red stroke | >100% of tolerance | "Straying - correct course" |
| Backend pass | Overall coverage ≥75% | Momentary red OK if corrected |

### Human Testing Results
- Pass rate: High (>80% for normal tracing)
- Average completion time: 2-4 seconds
- User feedback: Visual guidance helpful, not frustrating

---

## Issues Encountered & Solutions

### Issue 1: False Positives on Careful Human Tracers
**Problem:** Humans tracing slowly and carefully triggered regularity detection.
**Solution:** Lowered CV thresholds from 0.08 to 0.05, required multiple signals for rejection.

### Issue 2: Hesitation Check Too Strict
**Problem:** Some humans trace smoothly without micro-pauses, triggering hesitation flag.
**Solution:** Disabled hesitation as hard requirement (set `HESITATION_MIN_COUNT=0`), kept as soft signal.

### Issue 3: Ballistic Profile Check Too Strict
**Problem:** Humans with steady tracing speed failed ballistic profile check.
**Solution:** Relaxed thresholds (`BALLISTIC_THIRD_RATIO_MIN`: 0.7→0.5, `BALLISTIC_FINAL_DECEL_MIN`: 0.15→0.08).

### Issue 4: High Acceleration Rejection
**Problem:** Human quick movements triggered acceleration flag alone.
**Solution:** Changed `accel_flag` to require additional signal (`accel_flag AND regularity_flag`).

### Issue 5: Peek Rate Limit 429 Errors
**Problem:** Fast human movement triggered peek rate limiting.
**Solution:** Frontend handles 429 gracefully, continues without blocking user experience.

---

## Security Analysis

### What Makes This CAPTCHA Secure

1. **Asymmetric difficulty:** Easy for humans (follow visible line), hard for bots (must fake human imperfection)

2. **Progressive reveal:** Bots cannot pre-compute optimal trajectory without knowing full path

3. **Behavioral binding:** Success requires not just correct position but correct *manner* of movement

4. **Multi-signal detection:** Bypassing one check insufficient; must bypass all simultaneously

5. **Context-dependent validation:** Behavior must match task difficulty (slow at curves, fast on straights)

### Security Boundary

**Theoretical limit:** As bots become more sophisticated at mimicking human micro-patterns, they approach the boundary of indistinguishability. At this point, the CAPTCHA becomes a *cost function* rather than absolute prevention.

**Practical security:** Current state-of-the-art bots lack:
- Natural tremor simulation
- Context-appropriate hesitation
- Realistic acceleration profiles
- Authentic curvature-speed coupling

### Defense in Depth Layers

```
Layer 1: Peek Oracle Protection
    ↓ Bot cannot obtain full path efficiently
Layer 2: Timing Analysis
    ↓ Bot timing patterns detectable
Layer 3: Spatial Analysis
    ↓ Bot precision detectable
Layer 4: Behavioral Signals
    ↓ Bot lacks human micro-patterns
Layer 5: Curvature-Behavior Coupling
    ↓ Bot doesn't adapt to task difficulty
Layer 6: Client Binding (trajectory hash)
    ↓ Replay attacks prevented
```

---

## Key Conclusions

### 1. Detection Philosophy
> Detect **unnatural perfection**, not human errors. Bots fail by being too good.

### 2. Multi-Signal Requirement
> Single-signal detection causes false positives. Require multiple independent signals for rejection.

### 3. Context-Dependent Validation
> Static thresholds insufficient. Behavior must be validated *relative to task difficulty* (curvature-behavior coupling).

### 4. MTD Applied to Dynamics
> Moving Target Defense benefits interactive CAPTCHAs most when applied to interaction dynamics, not just randomized content.

### 5. Security as Cost Function
> Security gains are best expressed as attacker cost increase, not absolute prevention. The goal is making automation economically unviable.

### 6. Usability-Security Balance
> Generous tolerances with visual feedback allow human imprecision while behavioral analysis catches machine precision.

---

## Metrics Summary

| Metric | Target | Achieved |
|--------|--------|----------|
| Bot rejection rate | >90% | **100%** |
| Human pass rate | >80% | **~85%+** |
| False positive rate | <20% | **~15%** |
| Average human solve time | <5s | **2-4s** |
| Bot variants blocked | All tested | **6/6** |

---

## Future Work (Deferred)

### Phase 3: Usability Polish
- B1: Dynamic TTL scaling based on path length
- B3: Accessibility mode for motor-impaired users

### Phase 4: Advanced Features
- C2: Difficulty progression after failures
- C3: Enhanced logging for research analysis

---

## Technical Implementation Details

### Files Modified
| File | Changes |
|------|---------|
| `backend/main.py` | Ballistic profile check, hesitation detection, peek decay, trajectory hash verification |
| `backend/config.py` | Threshold tuning, new enforcement flags, peek decay parameters |
| `backend/models.py` | Added `trajectoryHash`, `clientTimingMs` fields |
| `backend/path.py` | Path variety (S-curves, diagonals, verticals) |
| `frontend/app.js` | Visual feedback (deviation colors), progress indicator, trajectory hash computation |

### Key Configuration Values
```python
# Tolerance
POINTER_CONFIG = {
    "mouse": {"tolerance_px": 20},
    "touch": {"tolerance_px": 30},
}

# Regularity detection (coefficient of variation)
min_dt_cv = 0.05  # timing variation threshold
min_dd_cv = 0.05  # distance variation threshold

# Ballistic profile
BALLISTIC_THIRD_RATIO_MIN = 0.5
BALLISTIC_FINAL_DECEL_MIN = 0.08

# Peek decay
PEEK_DECAY_MIN_ADVANCE_PX = 15
PEEK_DECAY_FACTOR = 0.5
```

---

## References

- Moving Target Defense principles applied to interactive systems
- Behavioral biometrics in human verification
- Mouse dynamics analysis for bot detection
- Coefficient of variation in timing analysis

---

*Document generated for FYP submission - February 2026*
