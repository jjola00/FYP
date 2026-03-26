# Beyond Recognition: Codebase State & Testing Context

**Project:** "Beyond Recognition: Reframing CAPTCHAs as Human-Usable Moving Target Defences"
**Author:** Oluwajomiloju (Jay) Olajitan, BSc Immersive Software Engineering, University of Limerick (2025/26)
**Supervisors:** Dr. Salaheddin Alakkari, Dr. Roisin Lyons
**Date of snapshot:** 2026-03-03

---

## 1. What This Project Is

A dual-CAPTCHA research system built around Moving Target Defense (MTD) principles (Jajodia et al., 2011). The core thesis: CAPTCHAs that use per-session procedural generation, high polymorphism, and short TTLs can reduce automated attack success and increase attacker cost while preserving human usability. Two prototype challenge types are implemented:

### 1a. Line Tracing CAPTCHA (Motor-Control)
- User holds down on a start dot and traces a progressively revealed Bezier path on an HTML5 Canvas.
- Server reveals path segments via a `/captcha/line/peek` endpoint as the user advances.
- On release, the full trajectory is submitted to `/captcha/line/verify` which runs 11+ anti-bot behavioral checks.
- 6 path families: horizontal LR/RL, vertical TB/BT, diagonal, S-curve. Weighted random selection per challenge.
- 10-second TTL, 75% coverage requirement, per-challenge tolerance jitter.

### 1b. Image Intersection CAPTCHA (Visual-Reasoning / Accessible Alternative)
- 2-3 procedurally generated colored lines (straight, quadratic Bezier) drawn on a dark canvas.
- User clicks on where lines intersect. Intersection coordinates are computed and stored server-side only, never sent to client.
- 30-second TTL (intentionally longer -- accessibility path), 15px click tolerance (mouse), 22px (touch), no grace clicks (any stray click = fail), 800ms minimum solve time.
- Exploits known VLM blind spots: ~58% VLM accuracy on line intersections (BlindTest, ACCV 2024), spatial click localization persistently hard even for GPT-5 (COGNITION, 2025).

---

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI 0.115.5, uvicorn, numpy, SQLite (WAL mode) |
| Frontend | Next.js 15.5, React 19, TypeScript, Tailwind CSS, Radix UI, HTML5 Canvas |
| Deployment | Backend on Render, Frontend on Vercel |
| Testing | pytest, custom bot_sim.py, shell scripts for ablation studies |
| Security | HMAC-SHA256 tokens, in-memory sliding-window rate limiting, per-challenge nonce replay prevention |

---

## 3. Backend Architecture (Key Files)

| File | Role |
|------|------|
| `backend/main.py` | FastAPI app, line CAPTCHA endpoints (`/captcha/line/new`, `/peek`, `/verify`), all behavioral analysis logic |
| `backend/path.py` | Bezier path generation (6 families), geometric utilities (curvature profile, lookahead, nearest-point projection) |
| `backend/config.py` | All tunable parameters. 13 boolean enforcement toggles for ablation testing via env vars |
| `backend/captcha_token.py` | HMAC-SHA256 token sign/verify with constant-time comparison |
| `backend/image_challenge.py` | Procedural image CAPTCHA generator. Straight + quadratic Bezier lines. Vectorized segment-segment intersection finding with numpy |
| `backend/image_validator.py` | Click validation via greedy distance matching with pointer-type-aware tolerances |
| `backend/image_routes.py` | Image CAPTCHA API (`/captcha/image/generate`, `/captcha/image/validate`) |
| `backend/db.py` | SQLite data layer. Tables: `challenges`, `attempt_logs`, `image_challenges`, `image_attempt_logs`, `feedback` |
| `backend/rate_limit.py` | In-memory sliding window. `challenge_limiter` (30/60s), `feedback_limiter` (3/60s) |
| `backend/models.py` | Pydantic request/response schemas for both CAPTCHA types |

---

## 4. Line CAPTCHA Behavioral Detection System

The verify endpoint runs these checks (each has an env-var toggle for ablation):

| Check | What It Detects | Config Toggle |
|-------|----------------|---------------|
| `too_perfect` | Mean + max deviation unrealistically small (bots follow path too precisely) | ENFORCE_BEHAVIOURAL |
| `regularity` | Low CV on timing intervals AND step distances (bots move with machine-uniform spacing) | ENFORCE_REGULARITY |
| `speed_const` | Speed std/mean ratio too low (bots maintain constant velocity) | ENFORCE_SPEED_LIMITS |
| `curvature_adaptation` | No speed difference between straight and curved segments (humans slow on curves, bots don't) | ENFORCE_CURVATURE_ADAPTATION |
| `ballistic_profile` | Flat velocity across first/mid/last thirds (humans accelerate early, decelerate late) | ENFORCE_BALLISTIC_PROFILE |
| `hesitation` | No micro-pauses at high-curvature decision points (humans hesitate, bots don't) | ENFORCE_HESITATION |
| `monotonic` | Path backtracking beyond 10px threshold | ENFORCE_MONOTONIC |
| `peek_state` | Peek oracle abuse (rate, budget, distance, progressive decay) | ENFORCE_PEEK_STATE/RATE/DISTANCE/BUDGET |
| `min_duration` | Solve time < 1000ms | ENFORCE_MIN_DURATION |

**Composite rejection logic** requires multiple corroborating signals to minimize false positives:
- `(speed_const AND regularity)` -> reject
- `(accel_flag AND regularity)` -> reject
- `(ballistic_flag AND hesitation_flag)` -> reject
- `too_perfect` alone -> reject (strongest single signal)

---

## 5. Frontend Components

| Component | Role |
|-----------|------|
| `page.tsx` | Main page. Tabbed UI ("Trace the Path" / "Spot the Crossings"). Failure nudging after 3 fails. Dispatches `captcha-verified` CustomEvent. |
| `captcha-canvas.tsx` | Line tracing canvas. requestAnimationFrame render loop, progressive peek, real-time deviation coloring, trajectory hash (SHA-256), human-friendly failure messages. |
| `image-captcha-canvas.tsx` | Intersection click canvas. Draws straight/Bezier lines, click markers, keyboard accessibility (arrow keys + Enter). |
| `tutorial-overlay.tsx` | One-time animated SVG tutorial for each challenge type. |
| `feedback-widget.tsx` | Floating feedback form with image upload, Discord webhook. |
| `api.ts` | Centralized API client. Session ID, fetch timeout (60s for cold starts), trajectory hash computation. |

---

## 6. Current Testing Infrastructure

### 6a. Bot Simulator (`scripts/bot_sim.py`)
A Python script that exercises the exact same API as the real frontend. Simulates a full bot lifecycle:
1. Create challenge (`/captcha/line/new`)
2. Iteratively peek for lookahead segments (`/captcha/line/peek`)
3. Step along the polyline with configurable: step size (px), timing (ms), spatial jitter, timing jitter, curvature-aware slowdown
4. Submit trajectory (`/captcha/line/verify`)

**CLI arguments:** `--step-px`, `--step-ms`, `--step-ms-jitter`, `--jitter-px`, `--curvature-aware`, `--curvature-slow-factor`, `--pointer-type`, `--attempts`, etc.

### 6b. Bot Test Runner (`scripts/run_bot_tests.sh`)
Runs 5 bot variants x N attempts each:
- `baseline`: no jitter, default speed
- `jitter_1_5`: 1.5px spatial jitter
- `slow_step_24`: slower step timing (24ms)
- `curvature_aware_slow`: curvature adaptation + timing jitter + slower base
- `touch_jitter_1_5`: touch pointer with 1.5px jitter

### 6c. Ablation Study Runner (`scripts/run_ablation_tests.sh`)
Launches separate backend instances on different ports, each with one security toggle disabled. Runs the full bot suite against each. Configurations tested: `hardened`, `no_peek_state`, `no_peek_rate`, `no_peek_distance`, `no_peek_budget`, `no_monotonic`, `no_speed_limits`, `no_min_duration`, `no_regularity`, `no_curvature_adaptation`, `no_behavioural`.

### 6d. Security Attack Tests (`backend/tests/security/`)
- `test_hough_transform.py`: Renders image CAPTCHA to numpy, runs OpenCV Canny + HoughLinesP, submits detected intersections. Tests straight vs curved line resistance.
- `test_vlm_attack.py`: Renders to PNG, sends to GPT-4o vision API, parses coordinate response, submits as clicks.
- `test_relay_timing.py`: Simulates relay delays from 0 to TTL+5s in 2s increments, verifies TTL enforcement.

### 6e. Results Aggregation
- `scripts/aggregate_ablation_results.py`: Parses results into CSV with Wilson score 95% CIs.
- `scripts/summary_attempts.py`: Queries SQLite for pass rates, solve times, failure breakdowns.
- `backend/scripts/export_metrics.py`: Exports structured JSON metrics for the FYP paper.

---

## 7. Testing Results So Far

### Line CAPTCHA (Bot Tests)

**Pre-hardening (Jan 16-20, 2026):** 200 attempts per config.
- Hardened: baseline 25%, slow_step_24 40%, curvature_aware_slow 30%, jitter variants 0%
- Removing curvature adaptation was the most devastating -- it was the dominant failure reason (~60% of all rejections)
- Removing behavioral analysis increased baseline pass rate by ~13pp
- Removing speed limits boosted curvature_aware_slow to 48.5%

**Jan 28 (relaxed timeout 7500ms):** slow_step_24 and curvature_aware_slow hit 100% pass rate -- showing time pressure itself is a defense.

**Post-hardening (Feb 4, 2026):** ALL bot variants at 0% pass rate across 200 attempts. New `too_perfect` detection catches bots that previously evaded curvature checks. This is the current state.

### Line CAPTCHA Final Metrics

| Metric | Target | Achieved |
|--------|--------|----------|
| Bot rejection rate | >90% | **100%** (all 6 variants) |
| Human pass rate | >80% | **~85%+** |
| False positive rate | <20% | **~15%** |
| Avg human solve time | <5s | **2-4s** |

### Image CAPTCHA (Security Tests)
- **VLM (GPT-4o):** Expected <60% solve rate based on BlindTest research (~58% VLM accuracy on line intersections)
- **Hough Transform:** Bezier curves significantly degrade detection accuracy vs straight-only lines
- **Relay timing:** 30s TTL with 15-25s typical relay overhead = very tight window

---

## 8. Research References (Key Papers Cited in FYP)

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

### Open-Source Tools/Datasets Referenced
- **Decaptcha** (Bursztein et al., 2011) -- generic text CAPTCHA solver
- **ImageBreaker** (Hossen et al., 2019) -- reCAPTCHA v2 online breaker
- **unCaptcha** (Bock et al., 2017) -- audio reCAPTCHA solver
- **BeCAPTCHA-Mouse** (Acien et al., 2021) -- behavioral bot detection
- **HuMIdb** -- 600-user public multimodal biometric dataset
- **MCA-Bench** (Wu et al., 2025) -- multimodal CAPTCHA robustness benchmark

---

## 9. What Has Been Tested vs. What Hasn't

### DONE (Local/Custom Bots)
- Custom `bot_sim.py` with 5 strategy variants against line CAPTCHA -- **all at 0% as of Feb 4**
- Full ablation study measuring contribution of each defense layer
- Comprehensive behavioral detection (11+ checks with composite rejection logic)
- Security tests for image CAPTCHA: Hough Transform, VLM (GPT-4o), relay timing

### NOT DONE (The Gap)
- **No testing against established open-source CAPTCHA-solving tools** that have published results against real CAPTCHAs (reCAPTCHA, hCaptcha, etc.)
- The current bot_sim.py is a custom script that exercises the API directly -- it does not represent the sophistication of tools that have been refined against production CAPTCHA systems
- No testing against:
  - Browser-automation-based solvers (Selenium/Playwright bots that interact with the actual frontend DOM/Canvas)
  - ML-based trajectory generators trained on human mouse movement datasets (e.g., BeCAPTCHA-Mouse style)
  - Vision-pipeline solvers beyond the single GPT-4o test (e.g., YOLO-based, ensemble approaches)
  - CAPTCHA-solving services/APIs (2Captcha, Anti-Captcha style approaches)
  - RL-trained mouse trajectory emulators (Akrout et al., 2019 style)
- No cross-validation against other CAPTCHA implementations to benchmark relative security
- The human usability study (30+ adults, mouse/touch, Likert frustration) is described in the methodology but results are not yet in the logs

---

## 10. Architecture Diagram (Simplified)

```
                          FRONTEND (Next.js / Vercel)
                    ┌──────────────────────────────────┐
                    │  page.tsx (tab switcher)          │
                    │  ├── captcha-canvas.tsx (line)    │
                    │  ├── image-captcha-canvas.tsx     │
                    │  ├── feedback-widget.tsx          │
                    │  └── tutorial-overlay.tsx         │
                    │  api.ts (fetch + session + hash)  │
                    └──────────────┬───────────────────┘
                                   │ HTTPS
                    ┌──────────────▼───────────────────┐
                    │      BACKEND (FastAPI / Render)    │
                    │                                    │
                    │  LINE CAPTCHA                      │
                    │  ├── /captcha/line/new   (path.py) │
                    │  ├── /captcha/line/peek  (path.py) │
                    │  └── /captcha/line/verify (main.py)│
                    │      └── 11+ behavioral checks     │
                    │                                    │
                    │  IMAGE CAPTCHA                     │
                    │  ├── /captcha/image/generate       │
                    │  │   └── image_challenge.py        │
                    │  └── /captcha/image/validate       │
                    │      └── image_validator.py         │
                    │                                    │
                    │  SHARED: token, rate_limit, db     │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────▼───────────────────┐
                    │  SQLite (data/captcha.db)          │
                    │  challenges, attempt_logs,         │
                    │  image_challenges,                 │
                    │  image_attempt_logs, feedback      │
                    └───────────────────────────────────┘
```

---

## 11. Key Config Values

| Parameter | Line CAPTCHA | Image CAPTCHA |
|-----------|-------------|---------------|
| TTL | 10s | 30s |
| Canvas | 400x400 | 400x400 |
| Mouse tolerance | 20px (path), jitter +/-2px | 15px (click), -- |
| Touch tolerance | 30px (path), jitter +/-3px | 22px (click), -- |
| Min solve time | 1000ms | 800ms |
| Coverage required | 75% | All intersections |
| Grace | -- | 0 (any stray click = fail) |
| Min samples | 20 trajectory points | -- |
| Rate limit | 30 req/60s | 30 req/60s |

---

## 12. File Tree (Source Only)

```
FYP/
├── backend/
│   ├── main.py                    # Line CAPTCHA API + behavioral analysis
│   ├── config.py                  # All parameters + enforcement toggles
│   ├── path.py                    # Bezier path generation + geometry
│   ├── captcha_token.py           # HMAC-SHA256 tokens
│   ├── db.py                      # SQLite layer
│   ├── models.py                  # Pydantic schemas
│   ├── image_challenge.py         # Image CAPTCHA generator
│   ├── image_validator.py         # Click validation
│   ├── image_routes.py            # Image CAPTCHA API
│   ├── feedback_routes.py         # Feedback + Discord webhook
│   ├── rate_limit.py              # Sliding window limiter
│   ├── requirements.txt
│   ├── render.yaml                # Deployment config
│   ├── scripts/
│   │   └── export_metrics.py      # JSON metrics export
│   └── tests/
│       ├── conftest.py            # Isolated test DB fixture
│       ├── test_image_challenge.py
│       ├── test_image_routes.py
│       ├── test_image_validator.py
│       ├── test_token.py
│       └── security/
│           ├── test_hough_transform.py  # CV attack
│           ├── test_vlm_attack.py       # GPT-4o attack
│           └── test_relay_timing.py     # CAPTCHA farm simulation
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Main page (tab switcher)
│   │   │   ├── layout.tsx         # Root layout + theme
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── captcha-canvas.tsx  # Line tracing canvas
│   │   │   ├── image-captcha-canvas.tsx  # Intersection click canvas
│   │   │   ├── feedback-widget.tsx
│   │   │   ├── tutorial-overlay.tsx
│   │   │   └── ui/               # Radix/shadcn components
│   │   ├── lib/
│   │   │   ├── api.ts            # API client + types
│   │   │   └── utils.ts
│   │   └── hooks/
│   └── package.json
├── scripts/
│   ├── bot_sim.py                 # Custom bot simulator
│   ├── run_bot_tests.sh           # 5-variant bot test runner
│   ├── run_ablation_tests.sh      # Ablation study runner
│   ├── aggregate_ablation_results.py  # Wilson CI CSV export
│   └── summary_attempts.py        # DB metrics summary
├── docs/
│   ├── FYP.md                     # Main thesis document
│   ├── fyp-additions.txt          # Curvature coupling findings
│   ├── image-captcha-architecture.md  # Image CAPTCHA spec
│   ├── image-captcha-research.md  # Research justification
│   ├── line-captcha-assessment.md # Vulnerability analysis
│   ├── line-captcha-results.md    # Final line CAPTCHA results
│   ├── line-research.txt          # Hardening research
│   └── phase-5-6-guide.md        # Integration & testing guide
├── logs/
│   ├── bot-tests/                 # Timestamped bot test results
│   └── ablations/                 # Timestamped ablation results
├── data/
│   └── captcha.db                 # SQLite database
└── src/
    └── line_captcha/
        └── config.ts              # Shared TS config constants
```

---

## 13. The Goal: Moving to Open-Source Bot Testing

The current testing uses a **custom-built bot simulator** (`bot_sim.py`) that directly calls the backend API with synthetic trajectory data. While this has been effective for iterating on defenses (achieving 100% rejection), it has a critical limitation for the FYP paper: **it doesn't demonstrate resistance against the class of tools that have actually broken production CAPTCHAs.**

The papers referenced in the FYP thesis document real-world attacks against reCAPTCHA, hCaptcha, and other systems using sophisticated, publicly available tools. To make the security evaluation credible and publishable, the testing needs to expand to include:

1. **Browser-automation bots** (Selenium/Playwright/Puppeteer) that interact with the real frontend Canvas element, not just the API -- testing whether the behavioral detection holds up against bots that must operate through the browser rendering pipeline
2. **ML-trained mouse trajectory generators** -- tools like BeCAPTCHA-Mouse that have been trained on real human movement datasets and can produce realistic-looking trajectories
3. **RL-based CAPTCHA solvers** -- approaches in the style of Akrout et al. (2019) that learned to bypass reCAPTCHA v3's behavioral scoring
4. **Vision-based solvers** for the image CAPTCHA -- beyond the single GPT-4o test, testing against YOLO pipelines, ensemble VLM approaches, and tools like the ones that broke reCAPTCHA v2 image grids
5. **CAPTCHA-solving service simulation** -- testing whether the TTL and token mechanics actually prevent relay-style attacks at the speeds commercial solving services operate

This would close the gap between "our custom bot can't beat it" and "established attack tools referenced in the literature can't beat it."
