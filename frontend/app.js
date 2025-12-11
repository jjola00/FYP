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

  ctx.fillStyle = "#22d3ee";
  ctx.beginPath();
  ctx.arc(start[0], start[1], 8, 0, Math.PI * 2);
  ctx.fill();
}

function drawSegments() {
  if (state.segments.length < 2) return;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  for (let i = 1; i < state.segments.length; i++) {
    const prev = state.segments[i - 1];
    const curr = state.segments[i];
    ctx.strokeStyle = `rgba(56, 189, 248, 1)`;
    ctx.lineWidth = curr.lineWidth;
    ctx.beginPath();
    ctx.moveTo(prev.x, prev.y);
    ctx.lineTo(curr.x, curr.y);
    ctx.stroke();
  }
}

function drawFrame() {
  clearCanvas();
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
