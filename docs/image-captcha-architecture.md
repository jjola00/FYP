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
- A canvas displaying 2–4 coloured lines (mix of straight and curved/Bézier)
- Lines intersect at 1–5 points
- Optional: faint distractor elements (non-intersecting lines, dots, geometric shapes)
- Clear instruction text: e.g., "Click on all the points where the lines cross"
- A countdown timer matching the line CAPTCHA's TTL

### What the User Does
- Clicks/taps on each intersection point
- Each click registers a marker on the canvas (visual feedback)
- Submits when done

### What Constitutes a Pass
- All intersection points clicked within a tolerance radius (~15px)
- No extra clicks on non-intersection areas (tolerance for 1 accidental click)
- Completed within the TTL

---

## 3. Technical Architecture

### 3.1 Challenge Generation (Server-Side)

```
┌──────────────────────────────────────────────────────┐
│                CHALLENGE GENERATOR                     │
│                                                       │
│  1. Random Parameters                                 │
│     ├── num_lines: random(2, 4)                       │
│     ├── line_types: random mix of straight + Bézier   │
│     ├── colours: random from distinct palette          │
│     ├── thickness: random(2px, 5px)                   │
│     ├── canvas_size: consistent (e.g., 400x400)       │
│     └── distractor_count: random(0, 3)                │
│                                                       │
│  2. Line Generation                                   │
│     ├── Generate control points for each line         │
│     ├── For Bézier: generate 2–3 control points       │
│     ├── Ensure lines actually intersect               │
│     └── Calculate exact intersection coordinates      │
│                                                       │
│  3. Distractor Generation (optional)                  │
│     ├── Non-intersecting lines in muted colours       │
│     ├── Geometric shapes (circles, dots)              │
│     └── Faint grid or pattern overlay                 │
│                                                       │
│  4. Output                                            │
│     ├── Canvas render data (sent to client)           │
│     ├── Intersection coordinates (stored server-side) │
│     ├── Challenge token (tied to session)             │
│     └── TTL timestamp                                 │
└──────────────────────────────────────────────────────┘
```

**Critical: intersection coordinates are NEVER sent to the client.** The server generates the challenge, sends only the visual data, and validates clicks against stored coordinates.

### 3.2 Intersection Calculation

For straight lines:
```
Line 1: y = m1*x + b1
Line 2: y = m2*x + b2
Intersection: x = (b2 - b1) / (m1 - m2), y = m1*x + b1
```

For Bézier curves — use numerical methods:
- Sample both curves at high resolution (e.g., 1000 points)
- Find pairs of sample points from different curves within a threshold distance
- Refine intersection via binary search / Newton-Raphson
- Store sub-pixel accurate coordinates server-side

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
│     ├── For each known intersection point:        │
│     │   └── Is there a click within TOLERANCE?    │
│     ├── Are there excess clicks? (allow 1 grace)  │
│     └── Total clicks ≈ total intersections?       │
│                                                   │
│  3. Timing Validation                             │
│     ├── Was it solved too fast? (< 500ms = bot)   │
│     └── Was it solved within TTL?                 │
│                                                   │
│  4. Result                                        │
│     ├── PASS: all intersections clicked, timing OK │
│     ├── FAIL: missing intersections or excess      │
│     └── EXPIRED: TTL exceeded                     │
│                                                   │
│  TOLERANCE_RADIUS = 15px (configurable)           │
│  MIN_SOLVE_TIME = 500ms                           │
└──────────────────────────────────────────────────┘
```

---

## 4. MTD Implementation Details

### 4.1 Movement Strategy (M) — Per-Session Randomisation

Every parameter below is randomised per challenge generation:

| Parameter | Range | Purpose |
|---|---|---|
| `num_lines` | 2–4 | Varies visual complexity |
| `line_type` | straight, quadratic Bézier, cubic Bézier | Defeats Hough Transform (straight-line detector) |
| `num_intersections` | 1–5 | Varies answer complexity |
| `line_colours` | Random from 8+ high-contrast palette | Prevents colour-based template matching |
| `line_thickness` | 2–5px | Varies edge detection characteristics |
| `canvas_background` | White/light grey/subtle gradient | Minor variation |
| `distractor_count` | 0–3 | Adds geometric mask-style confusion for CV |
| `distractor_types` | Lines, circles, dots, faint shapes | Diversity of noise |
| `instruction_text` | Randomly selected from equivalent phrasings | Defeats prompt template matching |

### 4.2 Timing Function (T)

- **TTL:** Match the line CAPTCHA's TTL exactly (TODO: confirm value)
- **Token generation:** Server issues a cryptographically signed token with embedded expiry
- **One-use:** Token is invalidated after first validation attempt (pass or fail)
- **No replay:** Same challenge cannot be submitted twice

### 4.3 Configuration Set (C) — Size Estimate

Conservative lower bound:
```
3 line counts × 3 line types × 8 colours × 5 intersection counts × 
100+ position variations × 4 distractor configs × 5 instruction variants
= 720,000+ unique configurations
```

With continuous randomisation of positions, the actual space is effectively infinite.

---

## 5. Anti-Bot Hardening Layers

### Layer 1: VLM Resistance (Architectural — research-backed)
- Line intersection detection: ~58% VLM accuracy (BlindTest, ACCV 2024)
- Spatial click localization: persistently hard, even for GPT-5 (COGNITION, 2025)
- Combined counting + localization: compounds difficulty

### Layer 2: Classical CV Resistance (Design-based — mixed evidence)
- Bézier curves defeat Hough Transform (straight-line detector)
- Distractor elements confuse edge detection pipelines
- Canvas rendering (not static image) prevents trivial extraction
- Varying line thickness and colours complicates thresholding

### Layer 3: Timing Resistance (Research-backed)
- Short TTL defeats CAPTCHA farm relay (30–45s relay > TTL)
- Minimum solve time (500ms) catches instant bot submissions
- One-use tokens prevent replay attacks

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

## 8. Difficulty Scaling

| Level | Lines | Intersections | Distractors | Line Types | Use Case |
|---|---|---|---|---|---|
| Easy | 2 | 1 | 0 | Straight only | First attempt, accessibility |
| Medium | 3 | 2–3 | 1–2 | Mix straight + Bézier | Standard challenge |
| Hard | 4 | 3–5 | 2–3 | Mostly Bézier | After failed attempts or suspicious behaviour |

Start at Easy/Medium. Escalate to Hard only if bot-like behaviour is detected (instant solves, repeated failures, suspicious patterns).

---

## 9. Tech Stack Considerations

This should integrate with the existing FYP codebase (FastAPI backend).

### Backend (Python / FastAPI)
- `challenge_generator.py` — procedural line + intersection generation
- `validator.py` — click validation with tolerance
- `token_manager.py` — cryptographic token issuance and validation
- Dependencies: `numpy` (geometry calculations), `secrets` (tokens)

### Frontend (React / Canvas)
- `ImageCaptcha.tsx` — main component
- HTML5 Canvas for rendering (no image files)
- Click event handling with coordinate capture
- Timer component
- State management for clicks (add, undo, submit)

### API Endpoints
```
POST /api/captcha/image/generate
  → Returns: { token, lines[], distractors[], ttl, instruction }

POST /api/captcha/image/validate
  ← Receives: { token, clicks: [{x, y}] }
  → Returns: { passed: boolean, message: string }
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

## 12. Open Questions / TODOs

- [ ] **Confirm line CAPTCHA TTL** — image CAPTCHA TTL must match
- [ ] **Decide exact tolerance radius** — 15px is initial estimate, needs user testing
- [ ] **Bézier intersection algorithm** — choose between sampling-based vs analytical approach
- [ ] **Distractor design** — what specific geometric elements confuse CV without confusing humans?
- [ ] **Colour blindness accessibility** — ensure line pairs are distinguishable under all common colour vision types (use shape/dash patterns as backup)
- [ ] **Maximum intersections** — research says subitizing limit is 4–6 items; cap at 4 for safety?
