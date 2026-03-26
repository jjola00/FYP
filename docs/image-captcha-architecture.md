# Image CAPTCHA Architecture: Line Intersection Click Challenge

## Purpose

This document defines the architecture for the **Ephemeral Image CAPTCHA** — a standalone, accessible CAPTCHA where users click on the intersection points of procedurally generated lines. It serves as an accessible alternative for users who cannot complete the motor-control line-tracing CAPTCHA.

Read `image-captcha-research.md` first — it contains the research justification for every design decision below.

---

## 1. System Context

```
┌─────────────────────────────────────────────────────┐
│                  DUAL CAPTCHA SYSTEM                 │
│                                                     │
│  ┌─────────────────┐     ┌────────────────────────┐ │
│  │  Line Tracing    │ OR  │  Image CAPTCHA          │ │
│  │  CAPTCHA          │     │  (this document)        │ │
│  │  (motor-control) │     │  (click intersections)  │ │
│  └─────────────────┘     └────────────────────────┘ │
│                                                     │
│  User selects based on ability/preference            │
│  Both framed through MTD ⟨M, T, C⟩                  │
└─────────────────────────────────────────────────────┘
```

The image CAPTCHA is **not** layered on top of the line CAPTCHA. They are **independent alternatives**. A user completes one OR the other.

---

## 2. Core Challenge Specification

### What the User Sees
- A canvas displaying 2–3 coloured lines (straight segments and quadratic Bezier curves)
- Lines intersect at 1–3 points
- Clear instruction text: randomly selected from 10 equivalent phrasings (e.g., "Click where the lines cross")
- A countdown timer (30 seconds)

### What the User Does
- Clicks/taps on each intersection point
- Each click registers a marker on the canvas (visual feedback)
- Submits when done

### What Constitutes a Pass
- All intersection points clicked within a tolerance radius (15px mouse, 22px touch/pen)
- No stray clicks — any click not near an intersection causes immediate rejection
- Completed within the 30-second TTL
- Solve time above 800ms minimum

---

## 3. Technical Architecture

### 3.1 Challenge Generation (Server-Side)

```
┌──────────────────────────────────────────────────────┐
│                CHALLENGE GENERATOR                     │
│                                                       │
│  1. Random Parameters                                 │
│     ├── num_lines: random(2, 3)                       │
│     ├── line_types: straight or quadratic Bezier      │
│     ├── colours: sampled without replacement from 8   │
│     ├── thickness: random uniform(2.0, 5.0) px        │
│     └── canvas_size: 400x400 px                       │
│                                                       │
│  2. Line Generation                                   │
│     ├── Generate control points per line              │
│     ├── Straight: 2 points, Quadratic: 3 points      │
│     ├── Min length enforced (40% / 30% of canvas)     │
│     └── Calculate intersections via vectorised numpy   │
│                                                       │
│  3. Intersection Validation                           │
│     ├── Accept if 1-3 intersections found             │
│     ├── Retry up to 50 times if out of range          │
│     └── Fallback: force intersection through existing │
│         curve at random angle                          │
│                                                       │
│  4. Output                                            │
│     ├── client_data: line defs, canvas config,        │
│     │   instruction text, intersection count          │
│     ├── server_data: intersection coordinates         │
│     │   (NEVER sent to client)                        │
│     ├── HMAC-SHA256 challenge token                   │
│     └── 30-second TTL                                 │
└──────────────────────────────────────────────────────┘
```

**Critical: intersection coordinates are NEVER sent to the client.** The server generates the challenge, sends only the visual data, and validates clicks against stored coordinates.

### 3.2 Intersection Calculation

Intersection detection uses a vectorised parametric cross-product method (implemented in `image_challenge.py`):

- Each curve is sampled at 500 points, producing a dense polyline
- All segment pairs across curves are tested using the 2D parametric formulation: `A1 + t*(A2-A1) = B1 + s*(B2-B1)`, solved via cross-products
- Valid intersections require both t and s in [0, 1]
- Raw intersection hits within a 3px radius are clustered by greedy centroid merging
- Points outside the canvas margin are filtered out

### 3.3 Client-Side Rendering

```
┌──────────────────────────────────────────────────┐
│              CLIENT (Browser)                     │
│                                                   │
│  ┌──────────────────────────────────────────────┐ │
│  │          HTML5 Canvas                         │ │
│  │                                               │ │
│  │  - Renders lines from server-provided data    │ │
│  │  - Captures click events (x, y)              │ │
│  │  - Shows visual feedback (marker on click)   │ │
│  │  - Countdown timer display                    │ │
│  │  - Submit button                              │ │
│  │                                               │ │
│  └──────────────────────────────────────────────┘ │
│                                                   │
│  On submit: sends array of click coordinates      │
│  + challenge token to server                      │
│                                                   │
│  NO intersection answers stored client-side       │
│  NO right-click / inspect element leakage         │
└──────────────────────────────────────────────────┘
```

**Rendering approach:** Server sends line definitions (start/end points, control points for Bézier, colours, thickness). Client renders via Canvas API. This means the "image" is never a downloadable file — a bot must screenshot and parse.

### 3.4 Server-Side Validation

```
┌──────────────────────────────────────────────────┐
│              VALIDATION ENGINE                    │
│                                                   │
│  Input: click_coordinates[], challenge_token       │
│                                                   │
│  1. Token Validation                              │
│     ├── Token exists and hasn't expired (TTL)     │
│     ├── Token hasn't been used before             │
│     └── Token matches session                     │
│                                                   │
│  2. Click Validation                              │
│     ├── Distance matrix: all clicks vs all        │
│     │   intersections (numpy vectorised)          │
│     ├── Any click > tolerance from ALL            │
│     │   intersections = stray click = FAIL        │
│     ├── Greedy assignment: each intersection      │
│     │   matched to nearest unused click           │
│     └── Pass only if all intersections matched    │
│                                                   │
│  3. Timing Validation                             │
│     ├── Was it solved too fast? (< 800ms = bot)   │
│     └── Was it solved within TTL? (30s)           │
│                                                   │
│  4. Result                                        │
│     ├── PASS: all intersections clicked, no stray │
│     │   clicks, timing OK                         │
│     ├── FAIL: missed intersections, stray clicks, │
│     │   too fast, or no clicks                    │
│     └── EXPIRED: TTL exceeded                     │
│                                                   │
│  TOLERANCE: 15px mouse, 22px touch/pen            │
│  MIN_SOLVE_TIME = 800ms                           │
└──────────────────────────────────────────────────┘
```

---

## 4. MTD Implementation Details

### 4.1 Movement Strategy (M) — Per-Session Randomisation

Every parameter below is randomised per challenge generation:

| Parameter | Range | Purpose |
|---|---|---|
| `num_lines` | 2–3 | Varies visual complexity |
| `line_type` | straight, quadratic Bezier | Defeats Hough Transform (straight-line detector) |
| `num_intersections` | 1–3 | Varies answer complexity |
| `line_colours` | Sampled without replacement from 8 high-contrast colours | Prevents colour-based template matching |
| `line_thickness` | 2.0–5.0px (uniform random) | Varies edge detection characteristics |
| `canvas_background` | White / light grey (#FFFFFF, #F5F5F5, #FAFAFA, #F0F0F0) | Minor variation |
| `instruction_text` | Randomly selected from 10 equivalent phrasings | Defeats prompt template matching |

### 4.2 Timing Function (T)

- **TTL:** 30 seconds (intentionally longer than the line CAPTCHA's 10s — accessibility path needs more time for spatial reasoning + clicking)
- **Token generation:** Server issues an HMAC-SHA256 signed token with embedded expiry
- **One-use:** Token is invalidated after first validation attempt (pass or fail); replays receive HTTP 410 Gone
- **No replay:** Same challenge cannot be submitted twice

### 4.3 Configuration Set (C) — Size Estimate

Conservative lower bound:
```
2 line counts × 2 line types × 8 colours × 3 intersection counts ×
100+ position variations × 10 instruction variants
= 96,000+ unique configurations
```

With continuous randomisation of positions, the actual space is effectively infinite.

---

## 5. Anti-Bot Hardening Layers

### Layer 1: VLM Resistance (Architectural — research-backed)
- Line intersection detection: ~58% VLM accuracy (BlindTest, ACCV 2024)
- Spatial click localization: persistently hard, even for GPT-5 (COGNITION, 2025)
- Combined counting + localization: compounds difficulty

### Layer 2: Classical CV Resistance (Design-based — mixed evidence)
- Quadratic Bezier curves defeat Hough Transform (straight-line detector)
- Canvas rendering (not static image) prevents trivial extraction
- Varying line thickness and colours complicates thresholding

### Layer 3: Timing Resistance (Research-backed)
- 30-second TTL constrains CAPTCHA farm relay (30–45s relay overhead leaves very tight window)
- Minimum solve time (800ms) catches instant bot submissions
- One-use tokens prevent replay attacks; replays receive HTTP 410

### Layer 4: Server-Side Security (Standard practice)
- Answer coordinates never exposed to client
- Cryptographic challenge tokens
- Rate limiting per IP/session

---

## 6. Data Flow

```
          Client                          Server
            │                               │
            │  1. Request CAPTCHA            │
            │──────────────────────────────>│
            │                               │ Generate challenge
            │                               │ Store intersections + token
            │  2. Challenge data             │
            │  (line defs, token, TTL)       │
            │<──────────────────────────────│
            │                               │
            │  Render on Canvas              │
            │  User clicks intersections     │
            │                               │
            │  3. Submit clicks + token      │
            │──────────────────────────────>│
            │                               │ Validate token
            │                               │ Check TTL
            │                               │ Compare clicks to stored coords
            │                               │ Check timing
            │  4. Result (pass/fail)         │
            │<──────────────────────────────│
            │                               │ Invalidate token
```

---

## 7. UI/UX Specification

### Layout
```
┌────────────────────────────────────────┐
│  Click on all the points where the     │
│  lines cross                    ⏱ 0:XX │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │                                  │  │
│  │        [CANVAS 400x400]          │  │
│  │                                  │  │
│  │   Lines rendered here            │  │
│  │   Click markers appear on tap    │  │
│  │                                  │  │
│  └──────────────────────────────────┘  │
│                                        │
│  Clicks: ●●○  (visual indicator)       │
│                                        │
│  [ Undo Last Click ]  [ Submit ✓ ]     │
│                                        │
│  Can't see the image? Request new one  │
└────────────────────────────────────────┘
```

### UX Requirements
- **Clear instructions** — always visible, plain language
- **Visual click feedback** — small coloured dot appears where user clicked
- **Undo** — user can remove their last click (mistakes happen)
- **Refresh** — user can request a new challenge if this one is confusing
- **Timer** — visible countdown, non-intrusive
- **Mobile-friendly** — touch targets large enough, canvas scales to viewport
- **Keyboard accessible** — tab to canvas, arrow keys to move cursor, enter to click (for accessibility)

### Colour Palette (High Contrast)
Lines should be visually distinct from each other and from distractors:
- Primary lines: bold, saturated colours (red, blue, green, orange, purple)
- Distractors: faint, desaturated, or dashed
- Background: white or very light grey
- Click markers: bright, contrasting (e.g., yellow with dark border)

---

## 8. Challenge Parameters

The implementation uses a single difficulty level with randomised parameters:

| Parameter | Range |
|---|---|
| Lines | 2–3 |
| Intersections | 1–3 |
| Line Types | Straight + Quadratic Bezier (random per line) |
| Colours | 8 high-contrast, sampled without replacement |
| Thickness | 2.0–5.0px uniform random |

No difficulty tiers are implemented. Variation comes from per-session randomisation (MTD movement strategy), not progressive difficulty.

---

## 9. Tech Stack Considerations

This should integrate with the existing FYP codebase (FastAPI backend).

### Backend (Python / FastAPI)
- `image_challenge.py` — procedural line + intersection generation (vectorised numpy)
- `image_validator.py` — click validation with pointer-type-aware tolerances
- `image_routes.py` — API endpoints (generate + validate)
- `captcha_token.py` — HMAC-SHA256 token signing/verification (shared with line CAPTCHA)
- Dependencies: `numpy` (geometry calculations), `fastapi`, `pydantic`

### Frontend (Next.js / React / Canvas)
- `image-captcha-canvas.tsx` — main canvas component (~340 lines)
- HTML5 Canvas rendering of lines and click markers
- Click event handling with coordinate capture
- Keyboard accessibility (arrow keys + Enter/Space for clicks, Backspace for undo)
- Timer display, click counter, undo/submit buttons

### API Endpoints
```
POST /captcha/image/generate
  → Returns: { challengeId, token, ttlMs, expiresAt, lines[], canvas, instruction, numIntersections }

POST /captcha/image/validate
  ← Receives: { challengeId, token, clicks: [{x, y}], pointerType }
  → Returns: { passed, reason, matched, expected, excess, tooFast }
```

---

## 10. Testing Strategy

### Usability Testing
- Target: >90% human first-attempt solve rate
- Target: <8 seconds average completion time
- Test with diverse users including those with colour vision differences
- Test on mobile devices (touch accuracy)

### Security Testing
- Feed challenges to GPT-4o / Gemini via screenshot → measure solve rate
- Run Hough Transform + intersection calculation pipeline → measure if curved lines defeat it
- Measure with and without distractors
- Test relay timing: can a CAPTCHA farm solve within TTL?

### Unit Testing
- Intersection calculation accuracy (known geometries)
- Tolerance radius validation (edge cases)
- Token expiry and one-use enforcement
- Rate limiting

---

## 11. Implementation Phases

### Phase 1: Core Generator
- Straight line generation with intersection calculation
- Server-side challenge storage
- Basic validation endpoint

### Phase 2: Canvas Rendering
- Client-side Canvas component
- Click handling and visual feedback
- Timer integration

### Phase 3: Bézier Curves
- Curved line generation
- Numerical intersection finding for curves
- Mixed straight + curved challenges

### Phase 4: Hardening
- Distractor elements
- Instruction text variation
- Minimum solve time check
- Token cryptography

### Phase 5: Integration
- Connect to existing dual-CAPTCHA system
- User choice flow (line tracing vs image CAPTCHA)
- Accessibility features (keyboard nav, screen reader support)
- Match TTL with line CAPTCHA

### Phase 6: Testing & Evaluation
- Usability study
- VLM attack testing
- Classical CV attack testing
- Write up results for FYP paper

---

## 12. Resolved Design Decisions

- **TTL:** 30 seconds (intentionally different from line CAPTCHA's 10s — accessibility path needs more time)
- **Tolerance radius:** 15px mouse, 22px touch/pen — empirically tuned during pilot testing
- **Intersection algorithm:** Vectorised segment-segment cross-product method with 500-point sampling and 3px greedy clustering
- **No distractors:** Removed from implementation — clean visual presentation prioritised for accessibility
- **No difficulty tiers:** Single randomised configuration; variation comes from MTD per-session generation
- **Maximum intersections:** Capped at 3 (within subitizing range)
