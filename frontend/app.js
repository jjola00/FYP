const API_BASE = "http://localhost:8000";

const config = {
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

const ui = {
  canvas: document.getElementById("captcha-canvas"),
  status: document.getElementById("status"),
  timer: document.getElementById("timer"),
  reloadBtn: document.getElementById("reload-btn"),
  lineSection: document.getElementById("line-section"),
};

const ctx = ui.canvas.getContext("2d");

const state = {
  challenge: null,
  expiresAtMs: 0,
  timerHandle: null,
  drawing: false,
  expired: false,
  solved: false,
  needsReset: false,
  startTs: 0,
  trajectory: [],
  segments: [],
  pointerProfile: "mouse",
  lookahead: [],
  lastPeekAt: 0,
  peekMinIntervalMs: 100,
  peekBlockedUntil: 0,
  nonce: "",
  token: "",
  finishPoint: null,
  showFinish: false,
  devicePixelRatio: window.devicePixelRatio || 1,
  distanceToEnd: null,
};

function setStatus(text, tone = "info") {
  ui.status.textContent = text;
  ui.status.style.color =
    tone === "error" ? "#f87171" : tone === "success" ? "#34d399" : "#22d3ee";
}

function setTimer(text) {
  ui.timer.textContent = text;
}

function formatFailureReason(data) {
  const reason = data?.reason || "unknown";
  console.log("[formatFailureReason] Formatting reason:", reason);
  switch (reason) {
    case "incomplete":
      return "Follow the line to the end.";
    case "insufficient_samples":
      return "Keep your finger/cursor down while tracing.";
    case "non_monotonic_time":
      return "Something went wrong. Try again.";
    case "too_fast":
      return "Slow down a little.";
    case "non_monotonic_path":
      return "Keep moving forward along the line.";
    case "speed_violation":
      return "Slow down a little.";
    case "behavioural":
      return "Try varying your speed naturally.";
    case "too_perfect":
      return "Relax - small wobbles are okay.";
    case "regularity":
      return "Try a more natural rhythm.";
    case "no_curvature_adaptation":
      return "Slow down a bit on curves.";
    case "no_ballistic_profile":
      return "Try accelerating at the start, slowing at the end.";
    case "no_hesitation":
      return "Take your time at the tricky bits.";
    case "jump_detected":
      return "Stay close to the line.";
    case "low_coverage":
      return "Follow the line more closely.";
    case "timeout":
      return "Time's up. Try again.";
    default:
      return "Couldn't verify. Try again.";
  }
}

function pointerProfileFromEvent(evt) {
  return evt.pointerType === "mouse" ? "mouse" : "touch";
}

function lineWidthForProfile(profile) {
  const tol = state.challenge?.tolerance;
  const dpr = state.devicePixelRatio || 1;
  if (profile === "mouse") {
    const base = tol?.mouse ? Math.max(3, Math.min(8, tol.mouse * 0.4)) : config.lineWidthMouse;
    return base * (dpr >= 2 ? 1.15 : 1);
  }
  const base = tol?.touch ? Math.max(6, Math.min(10, tol.touch * 0.35)) : config.lineWidthTouch;
  return base * (dpr >= 2 ? 1.15 : 1);
}

// Calculate distance from point to nearest point on a polyline
function distanceToPath(px, py, path) {
  if (!path || path.length < 2) return Infinity;
  let minDist = Infinity;
  for (let i = 0; i < path.length - 1; i++) {
    const [x1, y1] = path[i];
    const [x2, y2] = path[i + 1];
    const dx = x2 - x1;
    const dy = y2 - y1;
    const lenSq = dx * dx + dy * dy;
    let t = lenSq > 0 ? ((px - x1) * dx + (py - y1) * dy) / lenSq : 0;
    t = Math.max(0, Math.min(1, t));
    const nearX = x1 + t * dx;
    const nearY = y1 + t * dy;
    const dist = Math.hypot(px - nearX, py - nearY);
    if (dist < minDist) minDist = dist;
  }
  return minDist;
}

// Get stroke color based on distance from path (blue -> orange -> red)
function getStrokeColor(deviation, tolerance, alpha) {
  if (deviation <= tolerance * 0.5) {
    // On track - cyan/blue
    return `rgba(56, 189, 248, ${alpha.toFixed(3)})`;
  } else if (deviation <= tolerance) {
    // Near edge - orange warning
    return `rgba(251, 146, 60, ${alpha.toFixed(3)})`;
  } else {
    // Off path - red
    return `rgba(248, 113, 113, ${alpha.toFixed(3)})`;
  }
}

function startTimer() {
  if (state.timerHandle) clearInterval(state.timerHandle);
  state.timerHandle = setInterval(() => {
    if (state.solved || state.needsReset) {
      clearInterval(state.timerHandle);
      return;
    }
    const now = Date.now();
    const remaining = Math.max(0, state.expiresAtMs - now);
    setTimer(remaining ? `${Math.ceil(remaining / 1000)}s` : "");
    if (remaining <= 0) {
      console.log("[startTimer] Timer expired - setting expired flag");
      state.expired = true;
      state.drawing = false;
      state.needsReset = true;
      setStatus("Too slow.", "error");
      clearInterval(state.timerHandle);
    }
  }, 200);
}

async function fetchChallenge() {
  setStatus("Loading challenge...");
  state.drawing = false;
  state.expired = false;
  state.solved = false;
  state.needsReset = false;
  state.trajectory = [];
  state.segments = [];
  state.lookahead = [];
  try {
    const res = await fetch(`${API_BASE}/captcha/line/new`, { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.challenge = data;
    state.expiresAtMs = data.expiresAt * 1000;
    state.pointerProfile = "mouse";
    state.nonce = data.nonce;
    state.token = data.token;
    state.finishPoint = null;
    state.showFinish = false;
    setTimer("");
    // prime lookahead around start point
    await fetchLookahead(data.startPoint[0], data.startPoint[1], true);
    startTimer();
    setStatus("Ready. Press/touch start and trace the line.");
    drawFrame();
  } catch (err) {
    console.error(err);
    setStatus("Failed to load challenge.", "error");
  }
}

function clearCanvas() {
  ctx.fillStyle = "#0a0f1d";
  ctx.fillRect(0, 0, config.canvasWidth, config.canvasHeight);
}

function drawMarkers() {
  if (!state.challenge?.startPoint) return;
  const start = state.challenge.startPoint;
  // Save context state
  ctx.save();
  ctx.fillStyle = "#22d3ee";
  ctx.beginPath();
  ctx.arc(start[0], start[1], 8, 0, Math.PI * 2);
  ctx.fill();
  // Finish marker appears only when near end
  if (state.showFinish && state.finishPoint) {
    // Pulse effect when very close to finish
    const distToEnd = state.distanceToEnd ?? Infinity;
    const pulseThreshold = 60;
    let radius = 8;
    if (distToEnd < pulseThreshold && state.drawing) {
      // Pulsing radius based on proximity (closer = bigger pulse)
      const pulse = Math.sin(performance.now() / 150) * 0.3 + 1;
      const proximity = 1 - (distToEnd / pulseThreshold);
      radius = 8 + (4 * proximity * pulse);
    }
    ctx.fillStyle = "#34d399";
    ctx.beginPath();
    ctx.arc(state.finishPoint[0], state.finishPoint[1], radius, 0, Math.PI * 2);
    ctx.fill();
    // Show "Almost there!" when very close
    if (distToEnd < 30 && state.drawing) {
      ctx.fillStyle = "rgba(52, 211, 153, 0.8)";
      ctx.font = "12px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Almost there!", state.finishPoint[0], state.finishPoint[1] - 18);
    }
  }
  ctx.restore();
}

function drawGuideLine() {
  if (!state.lookahead.length) return;
  ctx.save();
  ctx.strokeStyle = "rgba(34, 211, 238, 0.6)"; // Cyan guide line
  ctx.lineWidth = 3;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.beginPath();
  ctx.moveTo(state.lookahead[0][0], state.lookahead[0][1]);
  for (let i = 1; i < state.lookahead.length; i++) {
    ctx.lineTo(state.lookahead[i][0], state.lookahead[i][1]);
  }
  ctx.stroke();
  ctx.restore();
}

function drawSegments() {
  if (state.segments.length < 2) return;

  const now = performance.now();
  const visibleMs = state.challenge?.trail?.visibleMs ?? config.trailVisibleMs;
  const fadeMs = state.challenge?.trail?.fadeoutMs ?? config.trailFadeMs;
  const maxAge = visibleMs + fadeMs;

  // Keep only recent history; compute alpha per segment for fade.
  const recent = [];
  for (const seg of state.segments) {
    const age = now - seg.createdAt;
    if (age > maxAge) continue;
    const alpha =
      age <= visibleMs ? 1 : Math.max(0, 1 - (age - visibleMs) / Math.max(1, fadeMs));
    recent.push({ ...seg, alpha });
  }
  state.segments = recent;
  if (recent.length < 2) return;

  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  for (let i = 1; i < recent.length; i++) {
    const prev = recent[i - 1];
    const curr = recent[i];
    const midX = (curr.x + prev.x) / 2;
    const midY = (curr.y + prev.y) / 2;
    const alpha = Math.min(prev.alpha, curr.alpha);
    // Use deviation-based coloring if available
    const deviation = curr.deviation ?? 0;
    const tolerance = curr.tolerance ?? 20;
    ctx.strokeStyle = getStrokeColor(deviation, tolerance, alpha);
    ctx.lineWidth = curr.lineWidth;
    ctx.beginPath();
    ctx.moveTo(prev.x, prev.y);
    ctx.quadraticCurveTo(prev.x, prev.y, midX, midY);
    ctx.stroke();
  }

  ctx.restore();
}

function drawFrame() {
  clearCanvas();
  drawGuideLine();
  drawMarkers();
  drawSegments();
}

async function verifyAttempt() {
  console.log("[verifyAttempt] Starting verification", {
    trajectoryLength: state.trajectory.length,
    minSamples: config.minSamples,
    expired: state.expired,
  });

  if (!state.challenge || state.trajectory.length < 2) {
    console.log("[verifyAttempt] No challenge or insufficient trajectory");
    return;
  }

  if (state.trajectory.length < config.minSamples) {
    console.log("[verifyAttempt] Insufficient samples - showing incomplete");
    setStatus("Captcha incompleted.", "error");
    state.needsReset = true;
    if (state.timerHandle) clearInterval(state.timerHandle);
    setTimer("");
    return;
  }

  setStatus("Verifying...");
  try {
    const body = {
      challengeId: state.challenge.challengeId,
      nonce: state.nonce,
      token: state.token,
      sessionId: "demo-session",
      pointerType: state.pointerProfile,
      osFamily: navigator.platform,
      browserFamily: navigator.userAgent,
      devicePixelRatio: state.devicePixelRatio,
      trajectory: state.trajectory,
    };
    const res = await fetch(`${API_BASE}/captcha/line/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    console.log("[verifyAttempt] Backend response:", data);

    if (data.passed) {
      state.solved = true;
      if (state.timerHandle) clearInterval(state.timerHandle);
      setTimer("");
      setStatus("Passed.", "success");
    } else {
      if (data.reason === "timeout") {
        console.log("[verifyAttempt] TTL expired - showing too slow");
        state.expired = true;
        state.needsReset = true;
        if (state.timerHandle) clearInterval(state.timerHandle);
        setStatus("Too slow.", "error");
      } else {
        console.log("[verifyAttempt] Failed with reason:", data.reason);
        setStatus(formatFailureReason(data), "error");
        state.needsReset = true;
        if (state.timerHandle) clearInterval(state.timerHandle);
        setTimer("");
      }
    }
  } catch (err) {
    console.error("[verifyAttempt] Error:", err);
    setStatus("Verification error.", "error");
  }
}

function handlePointerDown(evt) {
  evt.preventDefault();
  if (!state.challenge) return;
  if (state.solved) {
    setStatus("Passed. Click New Challenge.", "success");
    return;
  }
  if (state.needsReset) {
    console.log("[handlePointerDown] Needs reset, ignoring");
    return;
  }
  const now = Date.now();
  if (state.expired || now > state.expiresAtMs) {
    console.log("[handlePointerDown] Already expired before starting");
    state.expired = true;
    setStatus("Too slow.", "error");
    return;
  }
  state.pointerProfile = pointerProfileFromEvent(evt);
  const profile = state.pointerProfile === "mouse" ? "mouse" : "touch";
  const start = state.challenge?.startPoint;
  if (start) {
    const dist = Math.hypot(evt.offsetX - start[0], evt.offsetY - start[1]);
    const tol =
      profile === "mouse" ? state.challenge?.tolerance?.mouse : state.challenge?.tolerance?.touch;
    const startRadius = (tol ? tol : profile === "mouse" ? 20 : 30) * 1.25;
    if (dist > startRadius) {
      setStatus("Start on the blue dot.", "error");
      return;
    }
  }
  console.log("[handlePointerDown] Starting new trace");
  const lineWidth = lineWidthForProfile(profile);

  state.drawing = true;
  state.startTs = performance.now();
  state.trajectory = [];
  state.segments = [];
  ui.canvas.setPointerCapture(evt.pointerId);
  const relT = 0;
  state.trajectory.push({ x: evt.offsetX, y: evt.offsetY, t: relT });
  state.segments.push({
    x: evt.offsetX,
    y: evt.offsetY,
    createdAt: performance.now(),
    lineWidth,
  });
  drawFrame();
}

function handlePointerMove(evt) {
  evt.preventDefault();
  if (!state.drawing) return;
  const relT = performance.now() - state.startTs;
  state.trajectory.push({ x: evt.offsetX, y: evt.offsetY, t: Math.round(relT) });
  const profile = state.pointerProfile === "mouse" ? "mouse" : "touch";
  const lineWidth = lineWidthForProfile(profile);

  // Calculate deviation from guide path for visual feedback
  const deviation = distanceToPath(evt.offsetX, evt.offsetY, state.lookahead);
  const tol = profile === "mouse"
    ? (state.challenge?.tolerance?.mouse || 20)
    : (state.challenge?.tolerance?.touch || 30);

  state.segments.push({
    x: evt.offsetX,
    y: evt.offsetY,
    createdAt: performance.now(),
    lineWidth,
    deviation,
    tolerance: tol,
  });

  // Update distance to finish for progress feedback
  if (state.finishPoint) {
    state.distanceToEnd = Math.hypot(
      evt.offsetX - state.finishPoint[0],
      evt.offsetY - state.finishPoint[1]
    );
  }

  // Real-time guidance based on deviation
  if (deviation > tol * 1.5 && state.lookahead.length > 0) {
    setStatus("Getting off track...", "error");
  } else if (deviation > tol * 0.8 && state.lookahead.length > 0) {
    setStatus("Stay on the line", "info");
  } else if (state.distanceToEnd && state.distanceToEnd < 50) {
    setStatus("Almost there!", "success");
  } else {
    setStatus("Tracing...", "info");
  }

  fetchLookahead(evt.offsetX, evt.offsetY);
  drawFrame();
}

function handlePointerUp(evt) {
  evt.preventDefault();
  if (!state.drawing) return;
  console.log("[handlePointerUp] Pointer released, trajectory length:", state.trajectory.length);
  ui.canvas.releasePointerCapture(evt.pointerId);
  state.drawing = false;
  verifyAttempt();
}

function setupCanvas() {
  ui.canvas.width = config.canvasWidth;
  ui.canvas.height = config.canvasHeight;
  ui.canvas.addEventListener("pointerdown", handlePointerDown);
  ui.canvas.addEventListener("pointermove", handlePointerMove);
  ui.canvas.addEventListener("pointerup", handlePointerUp);
  ui.canvas.addEventListener("pointerleave", (evt) => {
    if (state.drawing) {
      console.log("[pointerleave] Pointer left canvas while drawing");
      ui.canvas.releasePointerCapture(evt.pointerId);
      state.drawing = false;
      state.needsReset = true;
      if (state.timerHandle) clearInterval(state.timerHandle);
      setTimer("");
      setStatus("Strayed too far.", "error");
    }
  });
  function tick() {
    drawFrame();
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function setupControls() {
  ui.reloadBtn.addEventListener("click", fetchChallenge);
}

async function fetchLookahead(x, y, force = false) {
  const now = performance.now();
  if (!force && now < state.peekBlockedUntil) return;
  if (!force && now - state.lastPeekAt < state.peekMinIntervalMs) return; // throttle
  state.lastPeekAt = now;
  if (!state.challenge) return;
  try {
    const res = await fetch(`${API_BASE}/captcha/line/peek`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        challengeId: state.challenge.challengeId,
        nonce: state.nonce,
        token: state.token,
        cursor: [x, y],
      }),
    });
    if (!res.ok) {
      if (res.status === 429) {
        state.peekMinIntervalMs = Math.min(250, state.peekMinIntervalMs + 25);
        state.peekBlockedUntil = now + state.peekMinIntervalMs;
      }
      return;
    }
    const data = await res.json();
    state.lookahead = data.ahead;
    state.distanceToEnd = data.distanceToEnd;
    state.showFinish = Boolean(data.finish);
    state.finishPoint = data.finish || null;
    state.peekMinIntervalMs = Math.max(100, state.peekMinIntervalMs - 5);
  } catch (err) {
    console.error("peek error", err);
  }
}

function init() {
  setupCanvas();
  setupControls();
  fetchChallenge();
}

init();
