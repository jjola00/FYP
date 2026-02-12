export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

// Request timeout in milliseconds (60s to handle Render free tier cold starts)
const REQUEST_TIMEOUT_MS = 60000;

export const captchaConfig = {
  canvasWidth: 400,
  canvasHeight: 400,
  trailVisibleMs: 400,
  trailFadeMs: 600,
  tooFastMs: 1000,
  requiredCoverage: 0.75,
  lineWidthMouse: 4,
  lineWidthTouch: 7,
  minSamples: 20,
};

// Generate or retrieve a persistent session ID for this browser session
function getSessionId(): string {
  if (typeof window === "undefined") return "server-render";

  let sessionId = sessionStorage.getItem("captcha_session_id");
  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem("captcha_session_id", sessionId);
  }
  return sessionId;
}

// Helper to fetch with timeout
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = REQUEST_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } finally {
    clearTimeout(timeoutId);
  }
}

// Compute trajectory hash for client binding (SHA-256, first 32 chars)
export async function computeTrajectoryHash(trajectory: TrajectoryPoint[], nonce: string, challengeId: string): Promise<string> {
  const trajStr = trajectory.map(s => `${s.x.toFixed(1)},${s.y.toFixed(1)},${s.t}`).join("|");
  const data = `${trajStr}:${nonce}:${challengeId}`;
  const encoder = new TextEncoder();
  const hashBuffer = await crypto.subtle.digest("SHA-256", encoder.encode(data));
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
  return hashHex.slice(0, 32);
}

export interface TrajectoryPoint {
  x: number;
  y: number;
  t: number;
}

export interface Challenge {
  challengeId: string;
  startPoint: [number, number];
  tolerance: {
    mouse: number;
    touch: number;
  };
  expiresAt: number;
  nonce: string;
  token: string;
}

export interface VerificationResponse {
  passed: boolean;
  reason?: string;
}

export interface LookaheadResponse {
  ahead: [number, number][];
  distanceToEnd: number;
  finish?: [number, number];
}

export async function fetchChallenge(): Promise<Challenge> {
  const res = await fetchWithTimeout(`${API_BASE}/captcha/line/new`, { method: "POST" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Failed to fetch challenge: HTTP ${res.status}${text ? ` - ${text}` : ""}`);
  }
  return await res.json();
}

export async function verifyAttempt(
  challenge: Challenge,
  trajectory: TrajectoryPoint[],
  pointerType: string,
  clientTimingMs: number,
  trajectoryHash: string
): Promise<VerificationResponse> {
  const body = {
    challengeId: challenge.challengeId,
    nonce: challenge.nonce,
    token: challenge.token,
    sessionId: getSessionId(),
    pointerType,
    osFamily: navigator.platform,
    browserFamily: navigator.userAgent,
    devicePixelRatio: window.devicePixelRatio || 1,
    trajectory,
    trajectoryHash,
    clientTimingMs,
  };

  const res = await fetchWithTimeout(`${API_BASE}/captcha/line/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Verification request failed: HTTP ${res.status}${text ? ` - ${text}` : ""}`);
  }

  return await res.json();
}

export async function fetchLookahead(
  challenge: Challenge,
  x: number,
  y: number
): Promise<LookaheadResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/captcha/line/peek`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      challengeId: challenge.challengeId,
      nonce: challenge.nonce,
      token: challenge.token,
      cursor: [x, y],
    }),
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }

  return await res.json();
}

// ─── Image CAPTCHA (line intersection click challenge) ──────────────────

export interface ImageLineDefinition {
  type: "straight" | "quadratic" | "cubic";
  points: number[][];
  colour: string;
  thickness: number;
}

export interface ImageChallenge {
  challengeId: string;
  token: string;
  ttlMs: number;
  expiresAt: number;
  lines: ImageLineDefinition[];
  canvas: {
    width: number;
    height: number;
    background: string;
  };
  instruction: string;
  numIntersections: number;
}

export interface ImageVerifyResponse {
  passed: boolean;
  reason: string;
  matched: number;
  expected: number;
  excess: number;
  tooFast: boolean;
}

export async function fetchImageChallenge(): Promise<ImageChallenge> {
  const res = await fetchWithTimeout(`${API_BASE}/captcha/image/generate`, {
    method: "POST",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Failed to fetch image challenge: HTTP ${res.status}${text ? ` - ${text}` : ""}`);
  }
  return await res.json();
}

export async function verifyImageAttempt(
  challenge: ImageChallenge,
  clicks: Array<{ x: number; y: number }>
): Promise<ImageVerifyResponse> {
  const res = await fetchWithTimeout(`${API_BASE}/captcha/image/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      challengeId: challenge.challengeId,
      token: challenge.token,
      clicks,
    }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Image verification failed: HTTP ${res.status}${text ? ` - ${text}` : ""}`);
  }

  return await res.json();
}
