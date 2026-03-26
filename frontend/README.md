# Beyond Recognition — Frontend

Next.js 15 / React 19 frontend for the dual CAPTCHA system.

## Components

- `captcha-canvas.tsx` — Line tracing CAPTCHA canvas (progressive path reveal, deviation coloring, trajectory hashing)
- `image-captcha-canvas.tsx` — Image intersection CAPTCHA canvas (click markers, keyboard accessibility)
- `tutorial-overlay.tsx` — One-time animated tutorial for each challenge type
- `feedback-widget.tsx` — Floating feedback form with Discord webhook
- `api.ts` — Centralized API client with session management

## Development

```bash
npm install
npm run dev
```

Runs on http://localhost:3000. Expects the backend at http://localhost:8000.
