# Ephemeral Line CAPTCHA (FYP)

Lightweight prototype of an ephemeral line-tracing CAPTCHA used for the FYP. The client draws on an HTML5 canvas while the FastAPI backend streams short path lookahead slices and verifies raw trajectories with behavioural checks. SQLite is used for logging during development.

## Stack
- Frontend: vanilla JS + Canvas (`frontend/`), calls `/captcha/line/new`, `/captcha/line/peek`, `/captcha/line/verify`.
- Backend: FastAPI + uvicorn (`backend/`), SQLite storage (`data/captcha.db` created automatically).
- Config constants for defaults live in `src/line_captcha/config.ts` (mirrored in `backend/config.py`).

## Prerequisites
- Python 3.10+ (tested with venv in `venv/`).

## Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```
Optional: set a secret for token signing (default is dev-only):
```bash
export LINE_CAPTCHA_SECRET="change-me"
```

## Running (two terminals)
1) Backend (from repo root):
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```
2) Frontend (from `frontend/`):
```bash
python3 -m http.server 3000
```
Then open http://localhost:3000 in the browser. The frontend talks to the backend at http://localhost:8000 (CORS is open in development).

## Notes
- Attempt logs and challenges are stored in `data/captcha.db`.
- Open tasks for the line CAPTCHA are listed in `tasks.txt`.
