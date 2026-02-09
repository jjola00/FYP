# Phase 5 & 6 Implementation Guide — Ephemeral Image CAPTCHA

This document is a self-contained reference for implementing the final two phases of the image CAPTCHA. It assumes no prior conversation context.

---

## Project Context

**Beyond Recognition** is a Final Year Project (FYP) implementing a dual-CAPTCHA system. Users complete one of two independent challenge types:

1. **Line Tracing CAPTCHA** (motor-control) — fully implemented. The user presses a start point and traces a progressively revealed Bézier path. Server validates trajectory, timing, and 11 behavioural signals (speed constancy, curvature adaptation, ballistic profile, hesitation, etc.).

2. **Image Intersection CAPTCHA** (accessible alternative) — Phases 1–4 complete. The user sees 2–4 procedurally generated lines (straight + Bézier curves) on an HTML5 Canvas and clicks the intersection points. Server validates clicks against stored coordinates within a tolerance radius.

Both CAPTCHAs are framed through an MTD (Moving Target Defense) ⟨M, T, C⟩ model: every challenge is procedurally unique, time-limited, and single-use.

**Key documents:**
- Architecture: `docs/image-captcha-architecture.md` (sections 5, 10, 11 are most relevant)
- Research: `docs/image-captcha-research.md` (VLM blind spots, spatial localization hardness)

---

## Current State of the Codebase

### Backend Files (`backend/`)

| File | Purpose |
|---|---|
| `main.py` | FastAPI app entry point. Line CAPTCHA endpoints: `POST /captcha/line/new`, `POST /captcha/line/peek`, `POST /captcha/line/verify`, `GET /health`. CORS middleware. Includes image router. |
| `config.py` | All constants for both CAPTCHAs. Line CAPTCHA: canvas size, timing, peek behaviour, 11 enforcement toggles, pointer profiles, behavioural thresholds. Image CAPTCHA: canvas size, tolerance, TTL, distractor settings, min solve time. All `ENFORCE_*` and `IMAGE_*` constants are env-configurable via `_env_bool()` / `os.getenv()`. |
| `models.py` | Pydantic request/response models for both CAPTCHAs. Line: `NewChallengeResponse`, `PeekRequest/Response`, `VerifyRequest/Response`, `TrajectorySample`. Image: `ImageLineDefinition`, `ImageDistractorShape`, `ImageNewChallengeResponse`, `ImageVerifyRequest/Response`, `ImageClickCoordinate`. |
| `db.py` | SQLite database layer. Tables: `challenges` (line CAPTCHA), `image_challenges` (image CAPTCHA), `attempt_logs` (line CAPTCHA verification audit trail). Functions: `init_db()`, `save_challenge()`, `get_challenge()`, `mark_challenge_used()`, `update_peek_progress()`, `save_attempt()`, `save_image_challenge()`, `get_image_challenge()`, `mark_image_challenge_used()`. |
| `path.py` | Line CAPTCHA path generation and geometry. Pure Python (no numpy). 6 path families (horizontal_lr/rl, vertical_tb/bt, diagonal, s_curve). Key exports: `generate_path(seed)`, `lookahead()`, `position_along_path()`, `min_distance_to_polyline()`, `curvature_profile()`, `cumulative_lengths()`. |
| `captcha_token.py` | HMAC-SHA256 token signing/verification shared by both CAPTCHAs. `sign(payload) → str`, `verify(token) → dict`. Token format: `base64(json).base64(hmac_sig)`. |
| `image_challenge.py` | Image CAPTCHA core generator. Generates lines (straight, quadratic Bézier, cubic Bézier), calculates intersections via vectorised numpy segment-segment tests, produces distractors (non-intersecting lines, near-miss fragments, geometric shapes). Main entry: `generate_challenge(difficulty)` → `{client_data, server_data}`. |
| `image_validator.py` | Image CAPTCHA click validation. `validate_clicks(clicks, intersections, solve_time_ms)` — tolerance-radius matching using numpy distance matrix, greedy matching, grace click allowance, min solve time enforcement (800ms, toggled by `ENFORCE_IMAGE_MIN_SOLVE`). |
| `image_routes.py` | Image CAPTCHA FastAPI Router. `POST /captcha/image/generate` — generates challenge, signs token, stores intersections in DB, returns client-safe data. `POST /captcha/image/validate` — verifies token, checks TTL, validates clicks, marks challenge as used. |
| `requirements.txt` | `fastapi==0.115.5`, `uvicorn==0.29.0`, `pydantic>=2.0`, `numpy>=1.24.0` |

### Frontend Files (`frontend/src/`)

| File | Purpose |
|---|---|
| `app/page.tsx` | Main page. Card layout with tabs ("Line CAPTCHA" / "Visual CAPTCHA"). Manages `activeTab` state, challenge loading, status/timer display, "New Challenge" button. Renders `CaptchaCanvas` or `ImageCaptchaCanvas` based on active tab. |
| `components/captcha-canvas.tsx` | Line CAPTCHA canvas component (~552 lines). HTML5 Canvas rendering with requestAnimationFrame loop, progressive path revelation via peek API, pointer capture, trail fade animation, colour-coded deviation feedback, trajectory hashing. Props: `challenge`, `onStatusChange`, `onTimerChange`, `onChallengeComplete`. |
| `components/image-captcha-canvas.tsx` | Image CAPTCHA canvas component (~340 lines). Renders challenge lines, distractor lines (with opacity via `globalAlpha`), distractor shapes (circles/rectangles), click markers (yellow #FACC15 with dark border #1a1a2e). Click counter dots, Undo Last / Submit buttons, "Request new challenge" link, countdown timer. Props: `challenge`, `onStatusChange`, `onTimerChange`, `onChallengeComplete`, `onRequestNew`. |
| `lib/api.ts` | API client. Types: `Challenge`, `TrajectoryPoint`, `ImageChallenge`, `ImageLineDefinition`, `ImageDistractorShape`, `ImageVerifyResponse`. Functions: `fetchChallenge()`, `verifyAttempt()`, `fetchLookahead()`, `computeTrajectoryHash()`, `fetchImageChallenge()`, `verifyImageAttempt()`. Uses `fetchWithTimeout()` with 60s timeout (for Render cold starts). Session ID via `sessionStorage`. |
| `components/theme-toggle.tsx` | Dark/light mode toggle button. |
| `components/theme-provider.tsx` | next-themes context wrapper. |

### Database Schema

**`challenges` (line CAPTCHA)**
```sql
id TEXT PRIMARY KEY, seed TEXT, points_json TEXT, path_length REAL,
ttl_ms INTEGER, nonce TEXT, tolerance_mouse REAL, tolerance_touch REAL,
jitter_mouse REAL, jitter_touch REAL, peek_pos REAL DEFAULT 0,
last_peek_at REAL, peek_count INTEGER DEFAULT 0,
nonce_used INTEGER DEFAULT 0, created_at REAL
```

**`image_challenges` (image CAPTCHA)**
```sql
id TEXT PRIMARY KEY, intersections_json TEXT, num_intersections INTEGER,
difficulty TEXT, ttl_ms INTEGER, used INTEGER DEFAULT 0, created_at REAL
```

**`attempt_logs` (line CAPTCHA audit trail)**
```sql
attempt_id TEXT PRIMARY KEY, session_id TEXT, challenge_id TEXT,
pointer_type TEXT, os_family TEXT, browser_family TEXT,
device_pixel_ratio REAL, path_seed TEXT, path_length_px REAL,
tolerance_px REAL, tolerance_jitter_px REAL, ttl_ms INTEGER,
started_at REAL, ended_at REAL, duration_ms REAL, outcome_reason TEXT,
coverage_ratio REAL, coverage_len_ratio REAL, mean_speed REAL,
max_speed REAL, pause_count INTEGER, pause_durations_json TEXT,
deviation_stats_json TEXT, speed_const_flag INTEGER, accel_flag INTEGER,
behavioural_flag INTEGER, speed_violation INTEGER,
too_perfect_flag INTEGER, bot_score REAL, regularity_dt_cv REAL,
regularity_dd_cv REAL, curvature_var_low REAL, curvature_var_high REAL,
trajectory_json TEXT, created_at REAL
```

### API Endpoints

| Method | Path | CAPTCHA | Purpose |
|---|---|---|---|
| POST | `/captcha/line/new` | Line | Issue new challenge |
| POST | `/captcha/line/peek` | Line | Get lookahead path hints |
| POST | `/captcha/line/verify` | Line | Validate trajectory + behavioural checks |
| POST | `/captcha/image/generate` | Image | Generate new click challenge |
| POST | `/captcha/image/validate` | Image | Validate click coordinates |
| GET | `/health` | — | Health check |

### Environment Variables (Image CAPTCHA)

All set via `os.getenv()` or `_env_bool()` in `config.py`:

| Variable | Default | Type | Purpose |
|---|---|---|---|
| `IMAGE_CAPTCHA_TTL_MS` | `30000` | int | Challenge time-to-live |
| `IMAGE_MIN_SOLVE_MS` | `800` | int | Minimum solve time (bot detection) |
| `ENFORCE_IMAGE_MIN_SOLVE` | `True` | bool | Toggle min-solve enforcement |
| `IMAGE_CLICK_TOLERANCE_PX` | `15` | int | Click-to-intersection match radius |
| `IMAGE_MAX_EXTRA_CLICKS` | `1` | int | Grace clicks beyond expected |
| `IMAGE_DISTRACTOR_OPACITY_MIN` | `0.3` | float | Distractor opacity lower bound |
| `IMAGE_DISTRACTOR_OPACITY_MAX` | `0.5` | float | Distractor opacity upper bound |
| `ENFORCE_IMAGE_DISTRACTORS` | `True` | bool | Toggle distractor generation |
| `IMAGE_NEAR_MISS_GAP_PX` | `8.0` | float | Gap for near-miss distractors |
| `IMAGE_BEZIER_SAMPLE_RESOLUTION` | `500` | int | Curve sampling density |
| `IMAGE_INTERSECTION_CLUSTER_RADIUS_PX` | `3.0` | float | Intersection dedup threshold |
| `IMAGE_MAX_GENERATION_RETRIES` | `50` | int | Retry budget per challenge |

### Environment Variables (Line CAPTCHA — selected)

| Variable | Default | Purpose |
|---|---|---|
| `ENFORCE_PEEK_STATE` | `True` | Peek state machine enforcement |
| `ENFORCE_PEEK_RATE` | `True` | Cap peek rate to ~10/s |
| `ENFORCE_BEHAVIOURAL` | `True` | Behavioural analysis blocking |
| `ENFORCE_TRAJECTORY_HASH` | `False` | Client trajectory hash binding |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | CORS origins |
| `LINE_CAPTCHA_SECRET` | `dev-secret-change-me` | HMAC signing key |

---

## Phase 5: Integration

### Goal

Wire both CAPTCHAs into a unified user experience with proper flow, failure handling, accessibility, and a verified state that a consuming application can use.

### 5.1 Tab Renaming and Subtitle

**File: `frontend/src/app/page.tsx`**

The current tabs read "Line CAPTCHA" and "Visual CAPTCHA". Rename for user-facing clarity:

- "Line Tracing" (or "Trace the Path")
- "Click Intersections" (or "Spot the Crossings")

Add a subtitle below the card title explaining the purpose:
```
"Verify you're human — choose a challenge type"
```

Keep the title "Beyond Recognition" as-is.

### 5.2 Mid-Attempt Reset

**Files: `page.tsx`, `captcha-canvas.tsx`, `image-captcha-canvas.tsx`**

Currently, switching tabs mid-attempt silently loads a new challenge for the other type. Add explicit handling:

- If the user has started an attempt (drawing has begun on line CAPTCHA, or clicks have been placed on image CAPTCHA), show a confirmation before switching tabs: "You have an attempt in progress. Switch anyway?"
- Implement this as a small inline warning, not a modal (keep it lightweight).
- Each canvas component should expose an `isAttemptInProgress` state or callback so `page.tsx` can check before switching.
- On the line CAPTCHA canvas (`captcha-canvas.tsx`), `state.drawing` or `state.trajectory.length > 0` indicates an attempt is in progress.
- On the image CAPTCHA canvas (`image-captcha-canvas.tsx`), `clicks.length > 0` indicates an attempt is in progress.

### 5.3 Unified Verified State

**Files: `page.tsx`, new file if needed**

A consuming application needs to know "this user passed CAPTCHA". Create a unified verified state:

- Add a `verified` state to `page.tsx`: `const [verified, setVerified] = useState(false)`.
- Both `handleChallengeComplete(success)` callbacks should set `verified = true` when `success === true`.
- When `verified` is true:
  - Show a green success banner replacing the canvas area (e.g., "Verified" with a checkmark)
  - Hide the tab switcher and "New Challenge" button
  - Expose the verified state to parent components or consuming applications. Options:
    - Call a prop callback: `onVerified?: () => void`
    - Dispatch a custom DOM event: `window.dispatchEvent(new CustomEvent("captcha-verified", { detail: { type: activeTab } }))`
    - Set a data attribute on the card element for external scripts to read
  - The consuming application decides what happens next (form submission, etc.)
- Add a "Reset" button (small, unobtrusive) that clears the verified state for testing/development.

### 5.4 Failure Tracking with Cross-Type Nudge

**File: `page.tsx`**

After 3 consecutive failures on one CAPTCHA type, gently suggest trying the other:

- Track consecutive failure count per type: `const [lineFailures, setLineFailures] = useState(0)` and `const [imageFailures, setImageFailures] = useState(0)`.
- In `handleChallengeComplete`, increment the failure counter on `success === false`, reset to 0 on `success === true`.
- When the counter hits 3, show a nudge message below the status text:
  ```
  "Having trouble? Try the [other type] instead."
  ```
  Make "other type" a clickable link that switches tabs and loads a new challenge.
- The existing `config.FALLBACK_AFTER_FAILURES = 3` in `backend/config.py` is already set for this purpose.
- Reset the failure counter when switching tabs.

### 5.5 Accessibility

**Files: `image-captcha-canvas.tsx`, `captcha-canvas.tsx`, `page.tsx`**

#### Keyboard Navigation

The image CAPTCHA canvas currently only supports pointer input. Add keyboard interaction:

- Make the canvas focusable: `tabIndex={0}`
- Arrow keys move a virtual cursor (visible crosshair overlay) in 5px increments (or 1px with Shift held)
- Enter/Space places a click at the virtual cursor position
- Backspace triggers undo (same as "Undo Last" button)
- Tab moves focus to Submit button, then to "New Challenge" button
- Escape cancels the current attempt and requests a new challenge

Implementation approach:
- Add a `keyboardCursor` state: `{ x: number, y: number } | null`
- On canvas focus, show the keyboard cursor at the center
- On arrow key, update position (clamped to canvas bounds)
- Draw the keyboard cursor as a crosshair (+) in the `drawFrame` function
- On Enter, call the same click-registration logic as `handlePointerDown`

#### ARIA Labels and Live Regions

- Canvas: `aria-label="CAPTCHA challenge canvas"` (already partially done)
- Timer: wrap in `<span aria-live="polite" aria-atomic="true">` — the current timer text in `page.tsx` should have `aria-live` (the status text already has it)
- Click counter: already has `aria-label={... clicks placed}` — verify it updates correctly
- On status changes (pass/fail/expired), announce via an `aria-live="assertive"` region
- Tab switcher: ensure `role="tablist"` and `role="tab"` are present (shadcn/ui Tabs likely handles this)

#### WCAG Contrast Verification

- Line colours from `COLOUR_PALETTE` in `image_challenge.py` are all saturated colours on a `#0a0f1d` dark background — verify each meets WCAG AA (4.5:1 contrast ratio)
- Click markers: yellow `#FACC15` on dark `#0a0f1d` — verify contrast
- Distractor colours from `_DISTRACTOR_COLOURS` are intentionally muted but must still be perceptible
- Use a contrast checker tool (e.g., WebAIM) to verify all combinations
- If any fail, adjust the problematic colours in `image_challenge.py`'s `COLOUR_PALETTE` or `_DISTRACTOR_COLOURS`

### 5.6 TTL Alignment

**Do NOT change the TTL values.** They are intentionally different:

- Line CAPTCHA TTL: 10s (`config.CHALLENGE_TTL_MS = 10_000`) — motor-control tracing is fast
- Image CAPTCHA TTL: 30s (`config.IMAGE_CHALLENGE_TTL_MS = 30000`) — accessibility path needs more time for spatial reasoning + clicking

Both are env-configurable if adjustment is needed later.

### 5.7 Definition of "Done" for Phase 5

Full flow works end-to-end:

1. Page loads → Line CAPTCHA tab active by default → challenge auto-loads
2. User can switch tabs → Image CAPTCHA loads → mid-attempt confirmation if needed
3. User completes either CAPTCHA → verified state shown → consuming app notified
4. After 3 consecutive failures on one type → nudge to try the other
5. Full keyboard navigation works on image CAPTCHA canvas
6. Screen reader announces status changes, timer, and results
7. All colour combinations pass WCAG AA contrast requirements
8. "New Challenge" and tab switching work correctly in all states (idle, in-progress, verified, expired)

---

## Phase 6: Testing & Evaluation

### Goal

Build the test harness and logging infrastructure to support the FYP evaluation. The actual VLM testing and usability studies happen outside the codebase — this phase is about making them possible and collecting the data.

### 6.1 Unit Tests

Create `backend/tests/` directory. Use `pytest`. Required test files:

#### `test_image_challenge.py` — Intersection Calculation Accuracy

```python
# Test cases:
# 1. Two perpendicular straight lines → exactly 1 intersection
# 2. Two parallel lines → 0 intersections
# 3. Known Bézier curves with pre-computed intersection → verify within 2px
# 4. Line entirely outside canvas margin → 0 intersections counted
# 5. Clustering: two raw intersections within 3px → merged to 1
# 6. Difficulty presets produce correct line/intersection count ranges
#    - easy: 2 lines, 1 intersection
#    - medium: 2-3 lines, 1-3 intersections
#    - hard: 3-4 lines, 2-5 intersections
# 7. generate_challenge() always returns at least 1 intersection (guarantee fallback)
# 8. Run 100 generations per difficulty → all produce valid intersection counts
```

#### `test_image_validator.py` — Tolerance and Edge Cases

```python
# Test cases:
# 1. Click exactly on intersection → pass
# 2. Click at tolerance boundary (15px away) → pass
# 3. Click at 16px away → fail (missed)
# 4. All intersections clicked + 1 extra → pass (grace click)
# 5. All intersections clicked + 2 extra → fail (too many extra)
# 6. Solve time 500ms → fail (too fast, threshold is 800ms)
# 7. Solve time 800ms → pass
# 8. Solve time 801ms → pass
# 9. 0 clicks submitted → fail
# 10. ENFORCE_IMAGE_MIN_SOLVE=False → fast solve still passes
```

#### `test_token.py` — Token Expiry and One-Use

```python
# Test cases:
# 1. sign() → verify() round-trip succeeds
# 2. Tampered token → verify() raises ValueError
# 3. Malformed token (no dot) → verify() raises ValueError
# 4. Token reuse: validate once → passes; validate again → HTTP 410 "already used"
# 5. Expired challenge: wait > TTL → validate returns "challenge expired"
```

#### `test_distractors.py` — Distractor Non-Intersection

```python
# Test cases:
# 1. Generate 100 medium challenges → no distractor intersects any challenge line
# 2. Generate 100 hard challenges → same verification
# 3. ENFORCE_IMAGE_DISTRACTORS=False → distractors list is empty
# 4. Easy difficulty → 0 distractors
# 5. Distractor opacity is within configured min/max range
```

#### `test_image_routes.py` — API Integration Tests

Use FastAPI's `TestClient` (requires `httpx`):

```python
# Test cases:
# 1. POST /captcha/image/generate → 200, response has required fields
# 2. Response does NOT contain intersections (server-side only)
# 3. POST /captcha/image/validate with valid clicks → passed=True
# 4. POST /captcha/image/validate with wrong clicks → passed=False
# 5. POST /captcha/image/validate with bad token → 400
# 6. POST /captcha/image/validate twice (replay) → 410
# 7. POST /captcha/image/validate after TTL → "challenge expired"
```

### 6.2 Image CAPTCHA Attempt Logging

**File: `backend/db.py`** — Create an `image_attempt_logs` table:

```sql
CREATE TABLE IF NOT EXISTS image_attempt_logs (
    attempt_id TEXT PRIMARY KEY,
    challenge_id TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    num_lines INTEGER NOT NULL,
    num_intersections INTEGER NOT NULL,
    num_distractors INTEGER NOT NULL,
    num_clicks INTEGER NOT NULL,
    matched INTEGER NOT NULL,
    excess INTEGER NOT NULL,
    passed INTEGER NOT NULL,
    reason TEXT NOT NULL,
    solve_time_ms REAL NOT NULL,
    too_fast INTEGER NOT NULL,
    clicks_json TEXT NOT NULL,
    created_at REAL NOT NULL
)
```

**File: `backend/image_routes.py`** — After validation, call `db.save_image_attempt()` with the full result. This mirrors how the line CAPTCHA logs to `attempt_logs`.

### 6.3 Security Test Harness

Create `backend/tests/security/` directory. These are scripts, not unit tests — they're run manually during evaluation.

#### `test_vlm_attack.py` — VLM Screenshot Attack

```python
# Script outline:
# 1. Generate N challenges via API
# 2. For each: render the challenge to a PNG using Pillow or matplotlib
#    (reconstruct from the client_data line definitions)
# 3. Feed each PNG to GPT-4o / Gemini via their API with prompt:
#    "How many intersection points are there and where are they?
#     Return coordinates as [(x,y), ...]"
# 4. Parse VLM response, submit as clicks
# 5. Record: VLM solve rate, accuracy of coordinates, time to respond
# 6. Compare with and without distractors (toggle ENFORCE_IMAGE_DISTRACTORS)
#
# Expected: <60% solve rate based on BlindTest research
```

#### `test_hough_transform.py` — Classical CV Attack

```python
# Script outline:
# 1. Generate N challenges, render to PNG
# 2. Run OpenCV Hough Transform pipeline:
#    - Convert to grayscale
#    - Canny edge detection
#    - HoughLinesP for straight lines
#    - Compute intersection of detected lines
# 3. Submit detected intersections as clicks
# 4. Record: solve rate for straight-only vs Bézier challenges
#
# Expected: Bézier curves significantly degrade Hough Transform accuracy
# Dependencies: opencv-python (add to test requirements, not main requirements.txt)
```

#### `test_relay_timing.py` — CAPTCHA Farm Relay Simulation

```python
# Script outline:
# 1. Generate a challenge
# 2. Simulate relay delay: wait N seconds (simulate screenshot + send + human solve + relay back)
# 3. Submit correct clicks after the delay
# 4. Record: at what relay delay does TTL start rejecting?
#
# Image CAPTCHA TTL is 30s, so relay must complete within that window
# Measure: minimum viable relay time for a human solver
# Expected: relay overhead (screenshot + transfer + solve + transfer back) ≈ 15-25s
#           leaves very tight margin within 30s TTL
```

### 6.4 Usability Metrics to Log

For the FYP writeup, the following metrics should be extractable from the logs:

**From `image_attempt_logs`:**
- First-attempt solve rate (target: >90%)
- Average solve time in ms (target: <8000ms)
- Failure reasons distribution (missed intersections, too many extra clicks, too fast, expired)
- Solve rate by difficulty level
- Average excess clicks per attempt

**From `attempt_logs` (line CAPTCHA — already exists):**
- First-attempt solve rate
- Average solve time
- Failure reasons distribution
- Bot score distribution
- Behavioural flag frequency

Create a `backend/scripts/export_metrics.py` script that queries both tables and produces a summary JSON or CSV for the FYP paper.

### 6.5 What to Measure for FYP Writeup

| Metric | Source | Target |
|---|---|---|
| Human first-attempt solve rate (image) | `image_attempt_logs` | >90% |
| Human avg completion time (image) | `image_attempt_logs` | <8s |
| VLM solve rate (GPT-4o) | `test_vlm_attack.py` | <60% |
| VLM solve rate (Gemini) | `test_vlm_attack.py` | <60% |
| Hough Transform solve rate (straight lines) | `test_hough_transform.py` | High (known weakness) |
| Hough Transform solve rate (Bézier curves) | `test_hough_transform.py` | Low (design goal) |
| Distractor impact on VLM | Compare with/without | Measurable reduction |
| Relay viability within TTL | `test_relay_timing.py` | Tight/infeasible margin |
| Human first-attempt solve rate (line) | `attempt_logs` | >90% |
| Human avg completion time (line) | `attempt_logs` | <5s |
| Bot detection rate (line) | `attempt_logs` where bot_score > 0 | >95% |

### 6.6 Definition of "Done" for Phase 6

1. `pytest backend/tests/` passes with all tests green
2. `image_attempt_logs` table exists and is populated on every validate call
3. Security test scripts exist and can be run manually
4. `export_metrics.py` produces a summary of all logged attempts
5. All unit tests cover the edge cases listed above
6. README or inline comments explain how to run each security test

---

## Key Design Decisions (Don't Change These)

These decisions are intentional and backed by research or user testing. A fresh session should preserve them.

| Decision | Value | Rationale |
|---|---|---|
| Image CAPTCHA TTL | 30s | Accessibility path — spatial reasoning + clicking takes longer than motor tracing. Line CAPTCHA is 10s. Both intentional. |
| Click tolerance | 15px | Balanced: 10px is frustrating on mobile, 20px is too forgiving for bots. Env-configurable via `IMAGE_CLICK_TOLERANCE_PX`. |
| Grace clicks | 1 | Forgiveness for one accidental misclick. More than 1 could be brute-force attempts. |
| Min solve time | 800ms | Below this is bot-like. Toggled by `ENFORCE_IMAGE_MIN_SOLVE`. |
| Distractor count | 0 easy / 1-2 medium / 2-3 hard | Easy is accessible first-attempt. Hard adds noise for suspicious users. |
| Canvas rendering | Client-side from server line definitions | Not a static image file — forces bots to screenshot and parse the DOM. Prevents trivial download and OCR. |
| Intersections never sent to client | Server-only storage | Core security property. `generate_challenge()` returns separate `client_data` and `server_data`. Only `client_data` is sent. Verify by checking that `ImageNewChallengeResponse` model has no intersection field. |
| HMAC-SHA256 token binding | One-use, expiry-embedded | Prevents replay, tampering, and cross-challenge submission. Shared `captcha_token.py` module for both CAPTCHAs. |
| All enforcement toggles env-configurable | `_env_bool()` pattern | Enables ablation testing for FYP evaluation — turn off individual security layers and measure impact. |
| Bézier curves (quadratic + cubic) | Always available at medium/hard | Defeats Hough Transform (straight-line detector). BlindTest research shows VLMs struggle more with curves. |
| Vectorised numpy intersection finding | Segment-segment cross-product method | Fast enough for real-time generation. Greedy clustering deduplicates within 3px. |
| Dark canvas background | `#0a0f1d` | Matches line CAPTCHA style. High contrast with saturated line colours. |
| Click markers | Yellow `#FACC15` with dark border `#1a1a2e` | Architecture doc spec. Visible on any line colour. |
| Instruction text randomised | 10 templates per singular/plural | Defeats prompt template matching by VLMs. |
