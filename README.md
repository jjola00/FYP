# Beyond Recognition — Dual CAPTCHA System (FYP)

A dual-CAPTCHA research system built around Moving Target Defense (MTD) principles. Two independent challenge types are implemented:

1. **Line Tracing CAPTCHA** (motor-control) — User traces a progressively revealed Bezier path. Server validates trajectory with 11 behavioural checks (speed constancy, regularity, curvature adaptation, ballistic profile, hesitation, etc.). 6 path families, 10-second TTL, 75% coverage requirement.

2. **Image Intersection CAPTCHA** (visual-reasoning) — User clicks where procedurally generated lines intersect. 2–3 lines (straight + quadratic Bezier), 1–3 intersections, 30-second TTL, 15px mouse / 22px touch click tolerance, 800ms minimum solve time.

Both CAPTCHAs use per-session procedural generation, HMAC-SHA256 tokens, and single-use challenges.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, uvicorn, numpy, SQLite (WAL mode) |
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Radix UI, HTML5 Canvas |
| Deployment | Backend on Render, Frontend on Vercel |
| Testing | pytest, custom bot simulator, ablation study scripts |

## Prerequisites

- Python 3.10+
- Node.js 18+

## Setup

### Backend
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

Optional: set a secret for token signing (default is dev-only):
```bash
export LINE_CAPTCHA_SECRET="change-me"
```

### Frontend
```bash
cd frontend
npm install
```

## Running (two terminals)

1) Backend (from repo root):
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

2) Frontend (from `frontend/`):
```bash
npm run dev
```

Then open http://localhost:3000. The frontend talks to the backend at http://localhost:8000 (CORS is open in development).

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/captcha/line/new` | Issue new line tracing challenge |
| POST | `/captcha/line/peek` | Get lookahead path segments |
| POST | `/captcha/line/verify` | Validate trajectory + behavioural checks |
| POST | `/captcha/image/generate` | Generate new intersection challenge |
| POST | `/captcha/image/validate` | Validate click coordinates |
| GET | `/health` | Health check |

## Testing

### Bot simulation (line CAPTCHA)
```bash
python scripts/bot_sim.py --attempts 10
```

### Ablation studies
```bash
bash scripts/run_ablation_tests.sh
```

### Unit tests
```bash
cd backend && python -m pytest tests/
```

## Notes

- Attempt logs and challenges are stored in `data/captcha.db` (created automatically).
- All enforcement toggles are env-configurable for ablation testing.
- See `docs/` for architecture, research, and results documentation.
