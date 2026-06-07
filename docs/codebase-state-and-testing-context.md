# Beyond Recognition: Codebase State & Testing Context

**Project:** "Beyond Recognition: Reframing CAPTCHAs as Human-Usable Moving Target Defences"
**Author:** Oluwajomiloju (Jay) Olajitan, BSc Immersive Software Engineering, University of Limerick (2025/26)
**Supervisors:** Dr. Salaheddin Alakkari, Dr. Roisin Lyons
**Date of snapshot:** 2026-03-31 (updated during live user study)

---

## 1. What This Project Is

A dual-CAPTCHA research system built around Moving Target Defense (MTD) principles (Jajodia et al., 2011). The core thesis: CAPTCHAs that use per-session procedural generation, high polymorphism, and short TTLs can reduce automated attack success and increase attacker cost while preserving human usability. Two prototype challenge types are implemented:

### 1a. Line Tracing CAPTCHA (Motor-Control)
- User holds down on a start dot and traces a progressively revealed Bezier path on an HTML5 Canvas.
- Server reveals path segments via a `/captcha/line/peek` endpoint as the user advances.
- On release, the full trajectory is submitted to `/captcha/line/verify` which runs 11 anti-bot behavioral checks.
- 6 path families: horizontal LR/RL, vertical TB/BT, diagonal, S-curve. Weighted random selection per challenge.
- 20-second TTL, 75% coverage requirement, per-challenge tolerance jitter.
- Progressive green finish dot glows as user approaches the end (visible from 80px away, pulses at 25px).

### 1b. Image Intersection CAPTCHA (Visual-Reasoning / Accessible Alternative)
- 2-3 procedurally generated colored lines (straight, quadratic Bezier) drawn on a dark canvas.
- User clicks on where lines intersect. Intersection coordinates are computed and stored server-side only, never sent to client.
- 20-second TTL, 15px click tolerance (mouse), 22px (touch), no grace clicks (any stray click = immediate fail), 800ms minimum solve time.
- numIntersections removed from client API response (security fix -- attacker cannot see expected count in DevTools).
- Exploits known VLM blind spots: ~58% VLM accuracy on line intersections (BlindTest, ACCV 2024), spatial click localization persistently hard even for GPT-5 (COGNITION, 2025).

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI 0.115.5, uvicorn, numpy, SQLite (WAL mode) |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Radix UI, HTML5 Canvas |
| Deployment | Backend on Render (free tier, ephemeral filesystem), Frontend on Vercel (auto-deploy) |
| Data persistence | Supabase (PostgreSQL) as cloud backup mirror of SQLite -- all attempt_logs, image_attempt_logs, questionnaire_responses mirrored via REST API |
| Testing | pytest, custom bot_sim.py, shell scripts for ablation studies |
| Security | HMAC-SHA256 tokens, in-memory sliding-window rate limiting, per-challenge nonce replay prevention |

---

## 3. Backend Architecture (Key Files)

| File | Role |
|------|------|
| `backend/main.py` | FastAPI app, line CAPTCHA endpoints (`/captcha/line/new`, `/peek`, `/verify`), questionnaire endpoint (`/questionnaire`), all behavioral analysis logic |
| `backend/path.py` | Bezier path generation (6 families), geometric utilities (curvature profile, lookahead, nearest-point projection) |
| `backend/config.py` | All tunable parameters. 13 boolean enforcement toggles for ablation testing via env vars. Supabase config. Production secret warning. |
| `backend/captcha_token.py` | HMAC-SHA256 token sign/verify with constant-time comparison |
| `backend/image_challenge.py` | Procedural image CAPTCHA generator. Straight + quadratic Bezier lines. Vectorized segment-segment intersection finding with numpy |
| `backend/image_validator.py` | Click validation via greedy distance matching with pointer-type-aware tolerances. No grace clicks. |
| `backend/image_routes.py` | Image CAPTCHA API (`/captcha/image/generate`, `/captcha/image/validate`). numIntersections not sent to client. |
| `backend/db.py` | SQLite data layer + Supabase backup mirror. Tables: `challenges`, `attempt_logs`, `image_challenges`, `image_attempt_logs`, `questionnaire_responses`, `feedback`. Every insert to attempt_logs, image_attempt_logs, questionnaire_responses, and feedback also POSTs to Supabase REST API (fire-and-forget, failures silently logged). |
| `backend/rate_limit.py` | In-memory sliding window. `challenge_limiter` (60/60s -- raised for NAT/shared IP in computer labs), `feedback_limiter` (3/60s) |
| `backend/models.py` | Pydantic request/response schemas for both CAPTCHA types + questionnaire |

---

## 4. Line CAPTCHA Behavioral Detection System

The verify endpoint runs 11 checks. Each has an env-var toggle for ablation:

| # | Check | What It Detects | Rejects Standalone? |
|---|-------|----------------|---------------------|
| 1 | `too_perfect` | Mean + max deviation unrealistically small | Yes |
| 2 | `speed_const` | Speed std/mean ratio too low | Composite only (with regularity) |
| 3 | `accel_flag` | Max acceleration spike exceeds cap | Composite only (with regularity) |
| 4 | `accel_sign_change` | Too few acceleration direction changes when speed is constant | Composite only (with regularity) |
| 5 | `speed_violation` | Instantaneous speed exceeds hard cap | Yes |
| 6 | `regularity` | Both timing CV and step-distance CV below minimums | Yes |
| 7 | `curvature_flag` | No speed adaptation between high/low curvature segments | Yes |
| 8 | `ballistic_flag` | Speed profile across thirds is too flat | Composite only (with hesitation) |
| 9 | `hesitation_flag` | Fewer than minimum micro-pauses at decision points | Composite only (with ballistic or regularity) |
| 10 | `progress_ok` | Path backtracking beyond 10px threshold | Yes |
| 11 | `too_fast` | Total solve duration below MIN_DURATION_MS (1000ms) | Yes |

**Composite rejection conditions** (require multiple corroborating signals):
- `accel_flag AND regularity` -> reject
- `speed_const AND regularity` -> reject
- `accel_sign_change AND regularity` -> reject
- `ballistic_flag AND hesitation_flag` -> reject
- `hesitation_flag AND regularity` -> reject

**Oracle-abuse detection** (peek endpoint, enforced via HTTP errors):
- Peek rate limit (60ms min interval)
- Peek budget (200 max requests)
- Peek distance (empty response if cursor too far from path)
- Peek state / progressive decay (max advance speed per second, reduced lookahead without cursor advance)

---

## 5. Study Flow (User Experience)

Participants follow this sequence:

1. **Info sheet** (`/info-sheet`) -- reads study description. Backend `/health` ping fires silently to warm Render cold start.
2. **Consent form** (`/consent`) -- 8 checkboxes, all required. Sets `study_consented` in sessionStorage. Clears tutorial flags.
3. **Image CAPTCHA first** (5 attempts) -- shown first to build confidence (high pass rate). Tutorial overlay shows on first visit (2 steps: how-to + timed warning). Challenge only loads after tutorial is dismissed.
4. **Interstitial** -- shows score (e.g. "You scored 4/5!").
5. **Line CAPTCHA** (5 attempts) -- tutorial overlay shows (2 steps: how-to with "trace naturally" advice + timed warning).
6. **Interstitial** -- shows score.
7. **Questionnaire** (`/questionnaire`) -- gated: requires `lineAttempts >= 5 AND imageAttempts >= 5`. Fields: device type, age range, tech comfort (1-5), CAPTCHA frequency (1-5), difficulty per type (1-5), frustration per type (1-5), free-text comments.
8. **Thank you** (`/thank-you`).

Key behaviors:
- Every completed attempt (pass or fail) counts toward the 5. No passes required to proceed.
- Confetti fires on each pass. Failure shows animated tutorial popup with reason-specific guidance; next challenge loads on popup dismiss.
- Consecutive failure morale nudge after 3 fails (encouragement text, no type switching).
- Attempt counter shown: "Attempt 3 of 5".
- Timeout auto-advances to next attempt (counts as failed attempt).
- `captcha-verified` CustomEvent dispatched on each pass.

---

## 6. Frontend Components

| Component | Role |
|-----------|------|
| `page.tsx` | Main page. Tabbed UI ("Trace the Path" / "Spot the Crossings"). Image CAPTCHA tab shown first. 5 attempts per type. Attempt tracking + pass tracking in sessionStorage. Interstitial with score after 5 attempts. |
| `captcha-canvas.tsx` | Line tracing canvas. requestAnimationFrame render loop, progressive peek, real-time deviation coloring, trajectory hash (SHA-256), progressive green finish dot (fades in from 80px, pulses at 25px), `completedRef` guard prevents double-fire of onChallengeComplete. |
| `image-captcha-canvas.tsx` | Intersection click canvas. Draws straight/Bezier lines, click markers, keyboard accessibility (arrow keys + Enter). Timeout calls onChallengeComplete. |
| `tutorial-overlay.tsx` | Multi-step tutorial popups per CAPTCHA type (2 steps each). `onComplete` callback triggers challenge load -- challenges are NOT fetched until tutorial is dismissed. Includes timer hint SVG. |
| `failure-tutorial.tsx` | Animated SVG failure-specific tutorials (incomplete, off-path, too-fast, timeout, natural for line; missed, excess, too-fast, timeout for image). |
| `feedback-widget.tsx` | Floating feedback form with Discord webhook. (Not used in study flow.) |
| `api.ts` | Centralized API client. Session ID via sessionStorage, fetch timeout (60s for cold starts), trajectory hash computation. Questionnaire submission endpoint. |

---

## 7. Database Schema

### SQLite (ephemeral on Render, backed up to Supabase)

**`attempt_logs`** (line CAPTCHA -- 35 columns):
attempt_id, session_id, challenge_id, pointer_type, os_family, browser_family, device_pixel_ratio, path_seed, path_length_px, tolerance_px, tolerance_jitter_px, ttl_ms, started_at, ended_at, duration_ms, outcome_reason, coverage_ratio, coverage_len_ratio, mean_speed, max_speed, pause_count, pause_durations_json, deviation_stats_json, speed_const_flag, accel_flag, behavioural_flag, speed_violation, too_perfect_flag, bot_score, regularity_dt_cv, regularity_dd_cv, curvature_var_low, curvature_var_high, trajectory_json, created_at

**`image_attempt_logs`** (15 columns):
attempt_id, challenge_id, num_lines, num_intersections, num_clicks, matched, excess, passed, reason, solve_time_ms, too_fast, clicks_json, pointer_type, tolerance_px, created_at

**`questionnaire_responses`** (12 columns):
id, session_id, device_type, age_range, tech_comfort, captcha_frequency, captcha1_difficulty, captcha1_frustration, captcha2_difficulty, captcha2_frustration, comments, created_at

**`challenges`** (line CAPTCHA active state), **`image_challenges`** (image CAPTCHA active state), **`feedback`** (unused)

### Supabase (persistent cloud mirror)
Same schema as SQLite for: attempt_logs, image_attempt_logs, questionnaire_responses, feedback. Inserted via REST API after every SQLite write (fire-and-forget, failures silently logged).

---

## 8. Key Config Values

| Parameter | Line CAPTCHA | Image CAPTCHA |
|-----------|-------------|---------------|
| TTL | 20s | 20s |
| Canvas | 400x400 | 400x400 |
| Mouse tolerance | 20px (path), jitter +/-2px | 15px (click) |
| Touch tolerance | 30px (path), jitter +/-3px | 22px (click) |
| Min solve time | 1000ms | 800ms |
| Coverage required | 75% | All intersections |
| Grace clicks | -- | 0 (stray click = fail) |
| Min samples | 20 trajectory points | -- |
| Rate limit | 60 req/60s (shared) | 60 req/60s (shared) |
| Finish reveal | 80px (progressive glow) | -- |
| Line types | N/A | straight, quadratic Bezier |
| Num lines | N/A | 2-3 |
| Intersections | N/A | 1-3 |

---

## 9. Testing Results

### 9a. Bot Tests (Line CAPTCHA)

**Post-hardening (Feb 4, 2026):** ALL bot variants at 0% pass rate across 200 attempts. 6 variants tested: baseline, jitter_1_5, slow_step_24, curvature_aware_slow, touch_jitter_1_5.

### 9b. Ablation Study
Curvature adaptation removal was the most devastating -- dominant failure reason (~60% of all rejections). Removing behavioral analysis increased baseline pass rate by ~13pp. Removing speed limits boosted curvature_aware_slow to 48.5%.

### 9c. Human User Study (LIVE -- started 2026-03-31)

As of latest data pull:

| Metric | Line CAPTCHA | Image CAPTCHA |
|--------|-------------|---------------|
| Pass rate (overall) | ~58% | ~88% |
| Mouse pass rate | ~92% (n=25) | ~96% (n=24) |
| Touch pass rate | ~46% (n=58) | ~85% (n=60) |
| Avg difficulty (Likert) | 3.2/5 | 1.7/5 |
| Avg frustration (Likert) | 3.4/5 | 1.9/5 |
| Median solve time (pass) | ~2.5s | ~3s |
| Completions | 16/17 sessions |
| Dropout rate | 1/17 (6%) |

**Key findings from live study:**
- Mouse users ace both CAPTCHAs (92% line, 96% image). Touch users struggle with line (46%) but handle image fine (85%).
- `incomplete` and `non_monotonic_time` are the dominant mobile failure reasons.
- `non_monotonic_time` is a mobile browser timestamp ordering bug, not user error -- causes false rejections on iOS.
- Finger occlusion is the #1 qualitative complaint (3+ comments: "my thumb covers the path").
- Desktop users rate line CAPTCHA difficulty 1-2/5; mobile users rate it 3-5/5.
- Image CAPTCHA consistently rated 1/5 difficulty and 1/5 frustration across devices.
- One outlier participant (Android) rated image harder than line (4/5 vs 2/5).

### 9d. Security Attack Tests (Image CAPTCHA)
- **VLM (GPT-4o):** Expected <60% solve rate based on BlindTest research
- **Hough Transform:** Bezier curves significantly degrade detection accuracy vs straight-only lines
- **Relay timing:** 20s TTL with 15-25s typical relay overhead = very tight window

---

## 10. Research References (Key Papers Cited in FYP)

### CAPTCHA Breaking
| Paper | What It Broke | Result |
|-------|--------------|--------|
| Goodfellow et al. (2014) | reCAPTCHA v1 text | 99.8% via end-to-end CNN |
| Hossen et al. (2019) -- ImageBreaker | reCAPTCHA v2 image grids | 92.4% online success |
| Sivakorn et al. (2016) | reCAPTCHA v2 image grids | 70.78% |
| Akrout et al. (2019) | reCAPTCHA v3 behavioral | 97.4% via RL mouse trajectories |
| Bock et al. (2017) -- unCaptcha | reCAPTCHA audio | 85.15% |
| Bursztein et al. (2011) -- Decaptcha | 13/15 text CAPTCHAs | Generic breaking tool |
| Plesner (2024, ETH Zurich) | reCAPTCHA v2 | 100% with YOLOv8 |

### VLM Limitations (Image CAPTCHA Basis)
| Paper | Finding |
|-------|---------|
| BlindTest (ACCV 2024) | Best VLM: 77.33% (Claude 3.5 Sonnet), avg ~58% on line intersection tasks. Failure is architectural. |
| COGNITION (Dec 2025) | 5 "persistently hard" task types even for GPT-5: Click_Order, Place_Dot, Pick_Area, Dice_Count, Patch_Select |
| Spatial CAPTCHA (Kharlamova et al., Oct 2025) | Humans ~99.8%, best VLM (Gemini-2.5-Pro) 31.0% |
| MCA-Bench (2025) | VLMs 96% on simple CAPTCHAs, 2.5% on complex ones requiring physical interaction |

### Behavioral / MTD
| Paper | Relevance |
|-------|-----------|
| Acien et al. (2021) -- BeCAPTCHA-Mouse | 93% human-vs-bot classification from mouse movements |
| Jajodia et al. (2011) | MTD foundations: `<M, T, C>` model |
| Cirjan (IEEE ICCAS 2025) | CAPTCHAs as MTD framework |
| Searles "Dazed & Confused" (USENIX 2023) | Polymorphic web code generation against bots |

---

## 11. Architecture Diagram (Simplified)

```
                          FRONTEND (Next.js / Vercel)
                    ┌──────────────────────────────────┐
                    │  /info-sheet → /consent → /       │
                    │  page.tsx (tab switcher)          │
                    │  ├── image-captcha-canvas.tsx     │
                    │  ├── captcha-canvas.tsx (line)    │
                    │  ├── tutorial-overlay.tsx         │
                    │  ├── failure-tutorial.tsx         │
                    │  └── /questionnaire → /thank-you  │
                    │  api.ts (fetch + session + hash)  │
                    └──────────────┬───────────────────┘
                                   │ HTTPS
                    ┌──────────────▼───────────────────┐
                    │      BACKEND (FastAPI / Render)    │
                    │                                    │
                    │  IMAGE CAPTCHA (shown first)       │
                    │  ├── /captcha/image/generate       │
                    │  └── /captcha/image/validate       │
                    │                                    │
                    │  LINE CAPTCHA                      │
                    │  ├── /captcha/line/new   (path.py) │
                    │  ├── /captcha/line/peek  (path.py) │
                    │  └── /captcha/line/verify (main.py)│
                    │      └── 11 behavioral checks      │
                    │                                    │
                    │  POST /questionnaire                │
                    │  GET  /health                       │
                    │                                    │
                    │  SHARED: token, rate_limit, db     │
                    └────────┬─────────────┬────────────┘
                             │             │
               ┌─────────────▼──┐   ┌──────▼──────────────┐
               │  SQLite         │   │  Supabase (backup)   │
               │  (ephemeral)    │   │  (persistent cloud)  │
               │  data/captcha.db│   │  REST API mirror     │
               └────────────────┘   └─────────────────────┘
```

---

## 12. File Tree (Source Only)

```
FYP/
├── backend/
│   ├── main.py                    # Line CAPTCHA API + behavioral analysis + questionnaire
│   ├── config.py                  # All parameters + enforcement toggles + Supabase config
│   ├── path.py                    # Bezier path generation + geometry
│   ├── captcha_token.py           # HMAC-SHA256 tokens
│   ├── db.py                      # SQLite layer + Supabase backup mirror
│   ├── models.py                  # Pydantic schemas (both CAPTCHAs + questionnaire)
│   ├── image_challenge.py         # Image CAPTCHA generator (straight + quadratic Bezier)
│   ├── image_validator.py         # Click validation (no grace clicks)
│   ├── image_routes.py            # Image CAPTCHA API (numIntersections not sent to client)
│   ├── feedback_routes.py         # Feedback + Discord webhook (unused in study)
│   ├── rate_limit.py              # Sliding window limiter (60 req/60s)
│   ├── requirements.txt
│   ├── render.yaml                # Deployment config
│   └── tests/
│       └── security/
│           ├── test_hough_transform.py
│           ├── test_vlm_attack.py
│           └── test_relay_timing.py
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx           # Main page (image first, 5 attempts each)
│       │   ├── info-sheet/page.tsx # Participant info + backend warm-up ping
│       │   ├── consent/page.tsx   # 8-checkbox consent form
│       │   ├── questionnaire/page.tsx # Post-task questionnaire (9 questions)
│       │   └── thank-you/page.tsx
│       ├── components/
│       │   ├── captcha-canvas.tsx  # Line tracing (progressive finish dot, completedRef guard)
│       │   ├── image-captcha-canvas.tsx  # Intersection clicks
│       │   ├── tutorial-overlay.tsx # Multi-step tutorials with onComplete callback
│       │   ├── failure-tutorial.tsx # Animated failure-specific guidance
│       │   └── ui/               # Radix/shadcn components
│       └── lib/
│           └── api.ts            # API client + types + questionnaire submission
├── scripts/
│   ├── bot_sim.py                 # Custom bot simulator
│   ├── dashboard.py               # Live study dashboard (Dash/Plotly, reads from Supabase)
│   ├── run_bot_tests.sh           # 5-variant bot test runner
│   ├── run_ablation_tests.sh      # Ablation study runner
│   ├── backup_and_reset_db.py     # SQLite backup + clear script
│   ├── aggregate_ablation_results.py
│   └── summary_attempts.py
├── docs/
│   ├── codebase-state-and-testing-context.md  # THIS FILE
│   ├── FYP.md                     # Main thesis document
│   ├── image-captcha-architecture.md
│   ├── image-captcha-research.md
│   ├── line-captcha-assessment.md
│   ├── line-captcha-results.md
│   └── phase-5-6-guide.md
├── data/
│   ├── captcha.db                 # SQLite database (ephemeral on Render)
│   └── pre_study_comments.md      # Saved pre-study tester comments
└── logs/
    ├── bot-tests/
    └── ablations/
```

---

## 13. Environment Variables (Production)

| Variable | Where | Purpose |
|----------|-------|---------|
| `LINE_CAPTCHA_SECRET` | Render | HMAC signing key (warns on startup if default) |
| `ALLOWED_ORIGINS` | Render | CORS: `https://fyp-mu-nine.vercel.app` |
| `SUPABASE_URL` | Render | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Render | Supabase service role key (bypasses RLS) |
| `NEXT_PUBLIC_API_BASE` | Vercel | Render backend URL |

---

## 14. Known Issues & Limitations

- **Render free tier**: Ephemeral filesystem (SQLite resets on deploy). Supabase backup is the persistent data store.
- **Render cold starts**: 30-60s wake-up. Mitigated by `/health` ping on info sheet page.
- **`non_monotonic_time` on iOS**: Mobile Safari sometimes emits pointer events with non-strictly-increasing timestamps. Causes false rejections. Left unchanged mid-study for consistency.
- **Finger occlusion on mobile**: User's finger covers the path being traced. Most common qualitative complaint. Future work: offset the visible path above the touch point.
- **`num_lines` in image_attempt_logs**: Always 0 (never populated with actual count). Harmless but unused column.
- **Session storage = per-tab**: New tab = fresh session. Participants could theoretically redo the study. Acceptable for supervised study.
- **No server-side session tracking**: Study completion gate is client-side (sessionStorage). Could be bypassed via DevTools. Low risk for voluntary study participants.
