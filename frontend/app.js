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
};

const ui = {
  canvas: document.getElementById("captcha-canvas"),
  status: document.getElementById("status"),
  timer: document.getElementById("timer"),
  reloadBtn: document.getElementById("reload-btn"),
  fallbackBtn: document.getElementById("fallback-btn"),
  lineSection: document.getElementById("line-section"),
  sliderSection: document.getElementById("slider-section"),
  slider: document.getElementById("slider"),
  sliderReset: document.getElementById("slider-reset"),
  backToLine: document.getElementById("back-to-line"),
  sliderStatus: document.getElementById("slider-status"),
};

const ctx = ui.canvas.getContext("2d");

const state = {
  challenge: null,
  expiresAtMs: 0,
  timerHandle: null,
  drawing: false,
  startTs: 0,
  trajectory: [],
  segments: [],
  pointerProfile: "mouse",
  failCount: 0,
};

function setStatus(text, tone = "info") {
  ui.status.textContent = text;
  ui.status.style.color =
    tone === "error" ? "#f87171" : tone === "success" ? "#34d399" : "#22d3ee";
}

function setTimer(text) {
  ui.timer.textContent = text;
}

function showSlider() {
  ui.lineSection.classList.add("hidden");
  ui.sliderSection.classList.remove("hidden");
}

function showLine() {
  ui.sliderSection.classList.add("hidden");
  ui.lineSection.classList.remove("hidden");
}

function pointerProfileFromEvent(evt) {
  return evt.pointerType === "mouse" ? "mouse" : "touch";
}

function lineWidthForProfile(profile) {
  return profile === "mouse" ? config.lineWidthMouse : config.lineWidthTouch;
}

function startTimer() {
  if (state.timerHandle) clearInterval(state.timerHandle);
  state.timerHandle = setInterval(() => {
    const now = Date.now();
    const remaining = Math.max(0, state.expiresAtMs - now);
    setTimer(`TTL: ${(remaining / 1000).toFixed(1)}s`);
    if (remaining <= 0) {
      setStatus("Challenge expired. Fetching new one...", "error");
      clearInterval(state.timerHandle);
      fetchChallenge();
    }
  }, 200);
}

async function fetchChallenge() {
  setStatus("Loading challenge...");
  state.drawing = false;
  state.trajectory = [];
  state.segments = [];
  try {
    const res = await fetch(`${API_BASE}/captcha/line/new`, { method: "POST" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    state.challenge = data;
    state.expiresAtMs = data.expiresAt * 1000;
    state.pointerProfile = "mouse";
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
  if (!state.challenge || !state.challenge.points?.length) return;
  const pts = state.challenge.points;
  const start = pts[0];

  // Save context state
  ctx.save();
  ctx.fillStyle = "#22d3ee";
  ctx.beginPath();
  ctx.arc(start[0], start[1], 8, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawGuideLine() {
  if (!state.challenge || !state.challenge.points?.length) return;
  if (!state.drawing) return;
  
  const pts = state.challenge.points;
  const revealDistance = 50; // How far ahead to show the guide line
  
  // Find the furthest point the user has reached
  let maxProgress = 0;
  if (state.segments.length > 0) {
    const lastSeg = state.segments[state.segments.length - 1];
    // Calculate how far along the path the user is
    for (let i = 0; i < pts.length; i++) {
      const dx = pts[i][0] - lastSeg.x;
      const dy = pts[i][1] - lastSeg.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < revealDistance) {
        maxProgress = Math.max(maxProgress, i);
      }
    }
    
    // Log progress every 10 segments
    if (state.segments.length % 10 === 0) {
      console.log(`Guide line progress: ${maxProgress}/${pts.length} points revealed`);
    }
  }
  
  // Draw the guide line up to slightly ahead of user's position
  if (maxProgress > 0) {
    ctx.save();
    ctx.strokeStyle = "rgba(34, 211, 238, 0.6)"; // Cyan guide line
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    
    const endIdx = Math.min(maxProgress + 5, pts.length - 1);
    for (let i = 1; i <= endIdx; i++) {
      ctx.lineTo(pts[i][0], pts[i][1]);
    }
    ctx.stroke();
    ctx.restore();
  }
}

function drawSegments() {
  if (state.segments.length < 2) return;
  
  // Save context state
  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.strokeStyle = "rgba(56, 189, 248, 1)";

  for (let i = 1; i < state.segments.length; i++) {
    const prev = state.segments[i - 1];
    const curr = state.segments[i];
    ctx.lineWidth = curr.lineWidth;
    ctx.beginPath();
    ctx.moveTo(prev.x, prev.y);
    ctx.lineTo(curr.x, curr.y);
    ctx.stroke();
  }
  
  // Restore context state
  ctx.restore();
  
  // Diagnostic logging (can be removed after testing)
  if (state.drawing && state.segments.length % 5 === 0) {
    console.log(`Drawing ${state.segments.length} segments`);
  }
}

function drawFrame() {
  clearCanvas();
  drawGuideLine();
  drawMarkers();
  drawSegments();
}

async function verifyAttempt() {
  if (!state.challenge || state.trajectory.length < 2) return;
  setStatus("Verifying...");
  try {
    const body = {
      challengeId: state.challenge.challengeId,
      sessionId: "demo-session",
      pointerType: state.pointerProfile,
      osFamily: navigator.platform,
      browserFamily: navigator.userAgent,
      trajectory: state.trajectory,
    };
    const res = await fetch(`${API_BASE}/captcha/line/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (data.passed) {
      setStatus(`Passed (coverage ${(data.coverageRatio * 100).toFixed(0)}%)`, "success");
      state.failCount = 0;
    } else {
      state.failCount += 1;
      setStatus(`Failed: ${data.reason}`, "error");
      if (data.reason === "timeout") {
        await fetchChallenge();
      } else if (state.failCount >= 3) {
        showSlider();
      } else {
        await fetchChallenge();
      }
    }
  } catch (err) {
    console.error(err);
    setStatus("Verification error.", "error");
  }
}

function handlePointerDown(evt) {
  evt.preventDefault();
  if (!state.challenge) return;
  const now = Date.now();
  if (now > state.expiresAtMs) {
    setStatus("Challenge expired. Fetching new one...", "error");
    fetchChallenge();
    return;
  }
  state.pointerProfile = pointerProfileFromEvent(evt);
  const profile = state.pointerProfile === "mouse" ? "mouse" : "touch";
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
  console.log(`PointerDown at (${evt.offsetX}, ${evt.offsetY}), lineWidth: ${lineWidth}`);
  drawFrame();
}

function handlePointerMove(evt) {
  evt.preventDefault();
  if (!state.drawing) return;
  const relT = performance.now() - state.startTs;
  state.trajectory.push({ x: evt.offsetX, y: evt.offsetY, t: Math.round(relT) });
  const profile = state.pointerProfile === "mouse" ? "mouse" : "touch";
  const lineWidth = lineWidthForProfile(profile);
  state.segments.push({
    x: evt.offsetX,
    y: evt.offsetY,
    createdAt: performance.now(),
    lineWidth,
  });
  // Log every 10th move event to avoid console spam
  if (state.segments.length % 10 === 0) {
    console.log(`PointerMove: ${state.segments.length} segments collected`);
  }
  drawFrame();
}

function handlePointerUp(evt) {
  evt.preventDefault();
  if (!state.drawing) return;
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
  ui.canvas.addEventListener("pointerleave", handlePointerUp);
  function tick() {
    drawFrame();
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

function setupControls() {
  ui.reloadBtn.addEventListener("click", fetchChallenge);
  ui.fallbackBtn.addEventListener("click", showSlider);
  ui.backToLine.addEventListener("click", () => {
    showLine();
    fetchChallenge();
  });
  ui.sliderReset.addEventListener("click", () => {
    ui.slider.value = 0;
    ui.sliderStatus.textContent = "Not solved";
    ui.sliderStatus.className = "slider-status";
  });
  ui.slider.addEventListener("input", () => {
    const val = Number(ui.slider.value);
    if (val >= 100) {
      ui.sliderStatus.textContent = "Slider solved";
      ui.sliderStatus.className = "slider-status success";
    } else {
      ui.sliderStatus.textContent = "Not solved";
      ui.sliderStatus.className = "slider-status";
    }
  });
}

function init() {
  setupCanvas();
  setupControls();
  fetchChallenge();
}

init();
