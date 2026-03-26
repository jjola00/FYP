# Ephemeral Image CAPTCHA Research: Line Intersection Click-Based Challenge

## Overview

This document summarises the research foundation for the **Ephemeral Image CAPTCHA** — a standalone, accessible CAPTCHA alternative within a dual-CAPTCHA system. This CAPTCHA is designed for users who cannot complete the motor-control line-tracing CAPTCHA (e.g., users with tremors, mobility impairments, or those using assistive technology).

The core challenge: **procedurally generated lines are displayed on a canvas, and the user clicks on the point(s) where the lines intersect.** The number of intersections ranges from 1–3 per challenge.

This CAPTCHA is framed through **Moving Target Defense (MTD)** principles, meaning every challenge is procedurally generated per-session, has a short TTL, and is never reused.

---

## 1. Why Line Intersection Clicking? The Research Basis

### 1.1 The VLM Blind Spot (Research-Backed)

The idea originates from **"Vision Language Models Are Blind"** (Rahmanzadehgervi et al., ACCV 2024). This peer-reviewed paper created the **BlindTest** benchmark — 7 trivially simple visual tasks that humans solve at ~100% accuracy but VLMs fail dramatically.

**Key findings on line intersections specifically:**
- 1,800 test images were generated, each containing two 2-segment piecewise-linear functions intersecting at 0, 1, or 2 points
- **Best VLM accuracy: 77.33%** (Claude 3.5 Sonnet). Average across 4 SOTA VLMs: ~58%
- **Human expected accuracy: 100%**
- VLMs perform worse as the distance between lines narrows
- The failure is **architectural**: linear probing experiments showed vision encoders contain sufficient visual information, but the language model fails to decode it into correct answers
- VLMs rely on "early fusion" to integrate a shallow vision encoder into an LLM — described by researchers as "essentially a knowledgeable brain without eyes"

**Source:** Rahmanzadehgervi, P., Bolton, L., Taesiri, M., Nguyen, A. "Vision language models are blind." ACCV 2024. Published at https://vlmsareblind.github.io/

### 1.2 Spatial Localization Is Even Harder Than Counting (Research-Backed)

BlindTest tested counting intersections (answer: a number). Our design asks users to **click on** intersections (answer: precise x,y coordinates). Research shows this is significantly harder for AI.

**COGNITION benchmark (December 2025)** tested 7 multimodal LLMs across 18 real-world CAPTCHA task types and identified 5 "persistently hard" task types, even for GPT-5:

- **Click_Order** — clicking targets in a specific order on a continuous canvas
- **Place_Dot** — placing a dot at a precise location
- **Pick_Area** — selecting a region defined by geometric cues
- **Dice_Count** — counting under visual clutter
- **Patch_Select** — cross-frame visual matching

These share structural hardness factors:
- "Fine-grained spatial localization: the solver must localize targets on a continuous canvas rather than select from a few discrete options"
- "MLLMs often describe the correct region yet output points or areas that fall outside the acceptable zone"
- Recurring error mode: "overconfident approximations in spatial decisions — the model outputs locations that are approximately right but fall outside the exact tolerance"

**Source:** COGNITION: From Evaluation to Defense against Multimodal LLM CAPTCHA Solvers. arXiv:2512.02318, December 2025.

### 1.3 Spatial CAPTCHAs Show Massive Human–AI Gap (Research-Backed)

**Spatial CAPTCHA benchmark (Kharlamova et al., October 2025):**
- **Humans: ~99.8% accuracy**
- **SOTA Gemini-2.5-Pro: 31.0%**
- Human accuracy dropoff between easy and hard difficulty bins is only ~6.7 percentage points
- Machine accuracy drops steeply with difficulty

**MCA-Bench (2025):**
- VLMs exceed 96% on simple CAPTCHAs
- Fall to **2.5%** on complex ones requiring physical interaction or multi-step reasoning
- "Visual confusion, interaction depth, and semantic complexity jointly drive attack difficulty"

**Sources:**
- Kharlamova et al. "Spatial CAPTCHA: Generatively Benchmarking Spatial Reasoning for Human-Machine Differentiation." arXiv:2510.03863, October 2025.
- MCA-Bench. arXiv:2506.05982, 2025.

### 1.4 Nobody Has Built This (Confirmed via Search)

Extensive search confirms:
- **No published paper** proposes line intersection detection/clicking as a CAPTCHA
- **No commercial product** uses this approach
- Lines have been used *in* CAPTCHAs before, but only as noise overlaid on distorted text (to confuse OCR), never as the challenge itself
- The closest related work is **Spatial CAPTCHA** (Kharlamova et al., 2025), which uses 3D perspective-taking and mental rotation — different challenge type entirely

**This represents a genuine gap in the literature that this FYP fills.**

---

## 2. Threat Model: What Attacks Must This CAPTCHA Resist?

### 2.1 VLM-Based Attacks (Strong Resistance — Research-Backed)

VLMs fail at both:
- **Counting** line intersections (~58% accuracy vs 100% human — BlindTest)
- **Localizing** precise coordinates on a canvas (persistently hard across all VLMs — COGNITION)

The click-based design exploits both weaknesses simultaneously.

### 2.2 Classical Computer Vision Attacks (Requires Hardening — Research-Backed + Inference)

**The threat:** The Hough Transform is a well-established algorithm (Hough, 1962; Duda & Hart, 1972) that detects straight lines in images. A bot could:
1. Screenshot the CAPTCHA image
2. Run edge detection (Canny) → Hough Transform → detect lines
3. Calculate intersection points algebraically
4. Click on the coordinates

**Research confirms Hough Transform is noise-resistant:** "The Hough transform has strong robustness and anti-interference ability in line detection" and is "much less sensitive to noise type" (Hough transform studies, IEEE).

**This means simple noise alone won't stop classical CV.**

**Countermeasures (mixed evidence levels):**

| Countermeasure | Evidence Level | Rationale |
|---|---|---|
| Use **curved/Bézier lines** instead of straight lines | **Logical inference** from Hough Transform maths — it parametrises straight lines as r = xcosθ + ysinθ. Curves break this parametrisation. No CAPTCHA-specific paper exists testing this. | Forces attackers to use expensive curve-fitting instead of trivial line detection |
| Add **visual distractor elements** (decoy lines, shapes, geometric masks) | **Research-backed** — geometric masks drop model Acc@1 by ~20 percentage points while remaining readable to humans (Seeing Through the Mask, 2024) | Humans distinguish target lines by colour/salience instantly; algorithms must determine which lines are "real" |
| **Server-side rendering** — generate and validate on server, never expose answer geometry to client | **Standard security practice** — COGNITION notes verification uses server-side tolerance windows | Prevents trivial image extraction and client-side answer leakage |
| **Short TTL** matching the line CAPTCHA | **Research-backed** — CAPTCHA farms complete challenges in 30–45 seconds; short TTLs make relay attacks infeasible | Maps to MTD timing function T |
| **Canvas rendering** (HTML5 Canvas, not a static image file) | **Engineering inference** — no specific paper, but standard anti-scraping practice | Makes clean image extraction harder; bot must screenshot and parse |

### 2.3 CAPTCHA Farm / Human Relay Attacks (Addressed by TTL)

- Farm workers complete CAPTCHAs in 30–45 seconds on average
- Cost: $0.94–$3.00 per 1,000 CAPTCHAs
- **Countermeasure:** TTL matching the line CAPTCHA ensures relay latency exceeds the challenge validity window

---

## 3. MTD Framing: ⟨M, T, C⟩ Model Applied

This CAPTCHA implements all five MTD principles (Jajodia et al., 2011; Cîrjan, IEEE ICCAS 2025):

### Movement Strategy (M) — What Changes
- Number of lines (2–3)
- Line type (straight, quadratic Bezier)
- Line colours, thickness, opacity
- Canvas size and background
- Number of intersections (1–3)
- Instruction phrasing variation (10 equivalent phrasings, randomly selected)

### Timing Function (T) — When It Changes
- Every session gets a fresh challenge
- TTL is 30 seconds (intentionally longer than line CAPTCHA's 10s — accessibility path needs more time)
- Challenge expires server-side; expired tokens are rejected

### Configuration Set (C) — The Space of Possible Challenges
Even conservatively:
- 2 possible line counts × 2 line types × 8 colours × 3 intersection counts × variable positions × 10 instruction variants = **thousands of discrete configurations, effectively infinite with continuous position randomisation**
- No two sessions ever see the same challenge
- No stable dataset for attackers to scrape or train on

---

## 4. Design Principles (Each With Evidence Source)

### Principle 1: Click-to-Locate, Not Type-a-Number
- **Source:** COGNITION (2025) — "fine-grained spatial localization" is a key structural hardness factor
- **Why:** Typing a number (1–5) gives 20% random guess success. Clicking coordinates on a canvas gives essentially 0% random guess success

### Principle 2: Use Curves/Bézier Lines, Not Only Straight Lines
- **Source:** Logical inference from Hough Transform mathematics (Duda & Hart, 1972)
- **Why:** Hough Transform detects straight lines trivially. Curves cannot be parametrised as r = xcosθ + ysinθ, forcing more expensive curve-fitting algorithms
- **Caveat:** No CAPTCHA-specific paper tests this. Empirical testing in the FYP would be a novel contribution

### Principle 3: Add Visual Distractors With Geometric Masking
- **Source:** "Seeing Through the Mask" (2024) — geometric masks drop model accuracy by ~20pp while remaining human-readable
- **Why:** Distractor lines/shapes that don't intersect with targets force bots to determine which elements are "real"

### Principle 4: Procedurally Generate Every Challenge Per Session
- **Source:** Spatial CAPTCHA (Kharlamova et al., 2025) — uses procedural content generation pipeline; Cîrjan (2025) — MTD principle of unpredictability
- **Why:** Eliminates scraping and dataset-based training attacks entirely

### Principle 5: Short TTL Matching Line CAPTCHA
- **Source:** CAPTCHA farm research — relay latency 30–45s; MTD timing function T
- **Why:** Makes relay attacks infeasible

### Principle 6: Vary Challenge Structure, Not Just Parameters
- **Source:** COGNITION (2025) — recommends "inclusion of multiple difficulty factors within a single challenge"
- **Why:** Sometimes "click where they cross," sometimes "click the intersection closest to the red dot," sometimes "how many crossings are above the line?" Prevents template-based solving

### Principle 7: Server-Side Rendering and Validation
- **Source:** COGNITION (2025) — verification uses server-side tolerance windows; standard security practice
- **Why:** Server knows exact intersection coordinates, validates clicks within pixel tolerance, never exposes answer to client

### Principle 8: Combine Counting + Localization
- **Source:** COGNITION (2025) — Dice_Count is persistently hard; counting under clutter stresses VLM spatial grounding
- **Why:** "Click on all 3 intersection points" requires both counting (how many?) and localization (where?) — independently hard for VLMs

### Principle 9: Keep It Accessible
- **Source:** Spatial CAPTCHA (2025) — human dropoff between difficulty bins is only ~6.7pp with clean geometric primitives
- **Target:** >90% human first-attempt solve rate, <8 seconds completion, clear instructions
- **Design:** 2–3 clearly coloured lines on a clean background, generous click tolerance (15px mouse, 22px touch)

---

## 5. Key References

| Paper | Venue | Year | Key Finding for This CAPTCHA |
|---|---|---|---|
| Rahmanzadehgervi et al. "Vision language models are blind" | ACCV | 2024 | VLMs ~58% on line intersections vs 100% human; architectural failure |
| COGNITION benchmark | arXiv:2512.02318 | 2025 | Click-based spatial localization persistently hard for GPT-5; design guidelines |
| Kharlamova et al. "Spatial CAPTCHA" | arXiv:2510.03863 | 2025 | 99.8% human vs 31% AI on spatial CAPTCHAs; procedural generation pipeline |
| MCA-Bench | arXiv:2506.05982 | 2025 | VLMs 96% on simple CAPTCHAs, 2.5% on complex spatial ones |
| "Seeing Through the Mask" | arXiv:2409.05558 | 2024 | Geometric masks drop model accuracy ~20pp, generalise across SOTA models |
| Jajodia et al. MTD foundations | Springer | 2011 | MTD ⟨M, T, C⟩ formal model |
| Cîrjan "CAPTCHAs as MTD" | IEEE ICCAS | 2025 | First paper framing CAPTCHAs through MTD lens |
| Searles et al. "Dazed & Confused" | USENIX Security | 2023 | Bots 85–99.8% vs humans 50–84%; CAPTCHA farms 30–45s relay |
| Plesner et al. reCAPTCHA broken | ETH Zurich | 2024 | 100% reCAPTCHAv2 solve rate with YOLOv8 |
| Duda & Hart, Hough Transform | Comm. ACM | 1972 | Straight line detection; basis for classical CV threat model |

---

## 6. What This FYP Contributes (Novelty)

1. **First CAPTCHA to use line intersection clicking as the challenge** — no prior art exists
2. **First empirical test of curved lines vs classical CV attacks** in a CAPTCHA context
3. **MTD implementation** — one of the first systems to build (not just theorise) a CAPTCHA under the ⟨M, T, C⟩ model
4. **Accessibility-first design** — specifically built as an accessible alternative for users who cannot complete motor-control CAPTCHAs
5. **Dual-modality MTD diversity** — the overall system (line tracing + image CAPTCHA) forces attackers to defeat two fundamentally different challenge types
