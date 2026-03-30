"use client";

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  captchaConfig,
  Challenge,
  TrajectoryPoint,
  fetchLookahead,
  verifyAttempt,
  computeTrajectoryHash
} from '@/lib/api';

interface CaptchaCanvasProps {
  challenge: Challenge | null;
  onStatusChange: (status: string, tone?: "info" | "error" | "success") => void;
  onTimerChange: (time: string) => void;
  onChallengeComplete: (success: boolean, reason?: string) => void;
  isAttemptInProgressRef?: React.MutableRefObject<() => boolean>;
}

interface CanvasSegment {
  x: number;
  y: number;
  createdAt: number;
  lineWidth: number;
  deviation?: number;
  tolerance?: number;
}

export function CaptchaCanvas({
  challenge,
  onStatusChange,
  onTimerChange,
  onChallengeComplete,
  isAttemptInProgressRef,
}: CaptchaCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // High-frequency data stored in refs to avoid React re-renders on every pointer move
  const trajectoryRef = useRef<TrajectoryPoint[]>([]);
  const segmentsRef = useRef<CanvasSegment[]>([]);
  const lookaheadRef = useRef<[number, number][]>([]);
  const drawingRef = useRef(false);
  const startTsRef = useRef(0);
  const pointerProfileRef = useRef<"mouse" | "touch">("mouse");
  const lastPeekAtRef = useRef(0);
  const peekMinIntervalRef = useRef(60);
  const peekBlockedUntilRef = useRef(0);
  const finishPointRef = useRef<[number, number] | null>(null);
  const showFinishRef = useRef(false);
  const distanceToEndRef = useRef<number | null>(null);
  const peekInFlightRef = useRef(false);

  // Low-frequency state that actually needs re-renders
  const [solved, setSolved] = useState(false);
  const [needsReset, setNeedsReset] = useState(false);
  const [expired, setExpired] = useState(false);
  const completedRef = useRef(false);  // guard: only call onChallengeComplete once per challenge
  const timerHandleRef = useRef<NodeJS.Timeout | null>(null);
  const dpr = useRef((typeof window !== 'undefined' ? window.devicePixelRatio : 1) || 1);

  // Timer effect — use challengeId as key so it resets cleanly on new challenge
  const challengeId = challenge?.challengeId;
  useEffect(() => {
    if (!challenge) return;

    // Immediately show the timer on first tick
    const remaining0 = Math.max(0, challenge.expiresAt * 1000 - Date.now());
    if (remaining0 > 0) onTimerChange(`${Math.ceil(remaining0 / 1000)}s`);

    const handle = setInterval(() => {
      const now = Date.now();
      const remaining = Math.max(0, challenge.expiresAt * 1000 - now);
      onTimerChange(remaining ? `${Math.ceil(remaining / 1000)}s` : "");

      if (remaining <= 0) {
        setExpired(true);
        drawingRef.current = false;
        setNeedsReset(true);
        onStatusChange("Too slow.", "error");
        if (!completedRef.current) { completedRef.current = true; onChallengeComplete(false, "timeout"); }
        clearInterval(handle);
      }
    }, 200);

    timerHandleRef.current = handle;

    return () => {
      clearInterval(handle);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [challengeId]);

  // Reset when challenge changes
  useEffect(() => {
    if (challenge) {
      trajectoryRef.current = [];
      segmentsRef.current = [];
      lookaheadRef.current = [];
      drawingRef.current = false;
      startTsRef.current = 0;
      lastPeekAtRef.current = 0;
      peekMinIntervalRef.current = 60;
      peekBlockedUntilRef.current = 0;
      finishPointRef.current = null;
      showFinishRef.current = false;
      distanceToEndRef.current = null;
      peekInFlightRef.current = false;
      setSolved(false);
      setNeedsReset(false);
      setExpired(false);
      completedRef.current = false;
      // Timer is managed by its own useEffect — don't clear it here
      // Prime lookahead at start point
      fetchLookahead(challenge, challenge.startPoint[0], challenge.startPoint[1])
        .then(data => {
          lookaheadRef.current = data.ahead;
          distanceToEndRef.current = data.distanceToEnd;
          showFinishRef.current = Boolean(data.finish);
          finishPointRef.current = data.finish || null;
        })
        .catch(() => {});
    }
  }, [challenge?.challengeId]);

  // Expose attempt-in-progress check to parent
  useEffect(() => {
    if (isAttemptInProgressRef) {
      isAttemptInProgressRef.current = () =>
        (drawingRef.current || trajectoryRef.current.length > 0) &&
        !solved &&
        !needsReset;
    }
  }, [isAttemptInProgressRef, solved, needsReset]);

  const formatFailureReason = (reason?: string) => {
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
  };

  const pointerProfileFromEvent = (evt: PointerEvent): "mouse" | "touch" => {
    return evt.pointerType === "mouse" ? "mouse" : "touch";
  };

  const lineWidthForProfile = (profile: "mouse" | "touch"): number => {
    const tol = challenge?.tolerance;
    const d = dpr.current;
    if (profile === "mouse") {
      const base = tol?.mouse ? Math.max(3, Math.min(8, tol.mouse * 0.4)) : captchaConfig.lineWidthMouse;
      return base * (d >= 2 ? 1.15 : 1);
    }
    const base = tol?.touch ? Math.max(6, Math.min(10, tol.touch * 0.35)) : captchaConfig.lineWidthTouch;
    return base * (d >= 2 ? 1.15 : 1);
  };

  const distanceToPath = (px: number, py: number, path: [number, number][]): number => {
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
  };

  const getStrokeColor = (deviation: number, tolerance: number, alpha: number): string => {
    if (deviation <= tolerance * 0.5) {
      return `rgba(56, 189, 248, ${alpha.toFixed(3)})`;
    } else if (deviation <= tolerance) {
      return `rgba(251, 146, 60, ${alpha.toFixed(3)})`;
    } else {
      return `rgba(248, 113, 113, ${alpha.toFixed(3)})`;
    }
  };

  // Convert client coordinates to canvas coordinates (account for CSS scaling)
  const getCanvasCoords = (evt: React.PointerEvent<HTMLCanvasElement>): { x: number, y: number } => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    return {
      x: (evt.clientX - rect.left) * scaleX,
      y: (evt.clientY - rect.top) * scaleY,
    };
  };

  // ── Drawing functions (read directly from refs, no React state) ──

  const drawFrame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear
    ctx.fillStyle = "#0a0f1d";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Guide line
    const la = lookaheadRef.current;
    if (la.length >= 2) {
      ctx.save();
      ctx.strokeStyle = "rgba(129, 140, 248, 0.9)";
      ctx.lineWidth = 3.5;
      ctx.setLineDash([10, 5]);
      ctx.beginPath();
      ctx.moveTo(la[0][0], la[0][1]);
      for (let i = 1; i < la.length; i++) {
        ctx.lineTo(la[i][0], la[i][1]);
      }
      ctx.stroke();
      ctx.restore();
    }

    // Markers
    if (challenge) {
      ctx.save();
      const start = challenge.startPoint;
      ctx.fillStyle = "rgba(56, 189, 248, 0.25)";
      ctx.beginPath();
      ctx.arc(start[0], start[1], 16, 0, 2 * Math.PI);
      ctx.fill();
      ctx.fillStyle = "rgba(56, 189, 248, 1.0)";
      ctx.beginPath();
      ctx.arc(start[0], start[1], 10, 0, 2 * Math.PI);
      ctx.fill();

      if (showFinishRef.current && finishPointRef.current) {
        const dist = distanceToEndRef.current ?? 80;
        // Progressive reveal: fade in from 80px to 20px, pulse when very close
        const fadeStart = 80;
        const fadeFull = 20;
        const t = Math.max(0, Math.min(1, (fadeStart - dist) / (fadeStart - fadeFull)));
        const opacity = t * 0.9;
        const baseRadius = 6 + t * 4; // 6px at edge, 10px when close
        const pulse = dist < 25 ? 1 + 0.15 * Math.sin(performance.now() / 150) : 0;
        const radius = baseRadius + pulse * 4;

        // Outer glow
        ctx.fillStyle = `rgba(34, 197, 94, ${opacity * 0.3})`;
        ctx.beginPath();
        ctx.arc(finishPointRef.current[0], finishPointRef.current[1], radius + 6, 0, 2 * Math.PI);
        ctx.fill();

        // Inner dot
        ctx.fillStyle = `rgba(34, 197, 94, ${opacity})`;
        ctx.beginPath();
        ctx.arc(finishPointRef.current[0], finishPointRef.current[1], radius, 0, 2 * Math.PI);
        ctx.fill();
      }
      ctx.restore();
    }

    // Segments (trail)
    const segs = segmentsRef.current;
    if (segs.length >= 2) {
      const now = performance.now();
      ctx.save();
      ctx.lineCap = "round";
      ctx.lineJoin = "round";

      for (let i = 1; i < segs.length; i++) {
        const prev = segs[i - 1];
        const curr = segs[i];
        const age = now - curr.createdAt;
        const alpha = Math.max(0, 1 - age / (captchaConfig.trailVisibleMs + captchaConfig.trailFadeMs));
        if (alpha <= 0) continue;

        const midX = (prev.x + curr.x) / 2;
        const midY = (prev.y + curr.y) / 2;
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
  }, [challenge]);

  const fetchPeek = useCallback((x: number, y: number, force = false) => {
    const now = performance.now();
    if (!force && now < peekBlockedUntilRef.current) return;
    if (!force && now - lastPeekAtRef.current < peekMinIntervalRef.current) return;
    if (peekInFlightRef.current && !force) return;

    lastPeekAtRef.current = now;
    if (!challenge) return;

    peekInFlightRef.current = true;
    fetchLookahead(challenge, x, y, pointerProfileRef.current)
      .then(data => {
        lookaheadRef.current = data.ahead;
        distanceToEndRef.current = data.distanceToEnd;
        showFinishRef.current = Boolean(data.finish);
        finishPointRef.current = data.finish || null;
        peekMinIntervalRef.current = Math.max(60, peekMinIntervalRef.current - 5);
      })
      .catch((err: any) => {
        if (err?.message?.includes("429")) {
          peekMinIntervalRef.current = Math.min(300, peekMinIntervalRef.current + 30);
          peekBlockedUntilRef.current = now + peekMinIntervalRef.current;
        }
      })
      .finally(() => {
        peekInFlightRef.current = false;
      });
  }, [challenge]);

  const verifyAttemptHandler = useCallback(async () => {
    const trajectory = trajectoryRef.current;
    if (!challenge || trajectory.length < 2) return;

    if (trajectory.length < captchaConfig.minSamples) {
      onStatusChange("Not enough movement recorded.", "error");
      setNeedsReset(true);
      if (timerHandleRef.current) clearInterval(timerHandleRef.current);
      if (!completedRef.current) { completedRef.current = true; onChallengeComplete(false, "insufficient_samples"); }
      return;
    }

    onStatusChange("Verifying...");
    try {
      const trajectoryHash = await computeTrajectoryHash(
        trajectory,
        challenge.nonce,
        challenge.challengeId
      );
      const clientTimingMs = performance.now() - startTsRef.current;

      const data = await verifyAttempt(
        challenge,
        trajectory,
        pointerProfileRef.current,
        clientTimingMs,
        trajectoryHash
      );

      if (data.passed) {
        setSolved(true);
        if (timerHandleRef.current) clearInterval(timerHandleRef.current);
        onTimerChange("");
        onStatusChange("Passed.", "success");
        if (!completedRef.current) { completedRef.current = true; onChallengeComplete(true); }
      } else {
        if (data.reason === "timeout") {
          setExpired(true);
          setNeedsReset(true);
          if (timerHandleRef.current) clearInterval(timerHandleRef.current);
          onStatusChange("Too slow.", "error");
        } else {
          onStatusChange(formatFailureReason(data.reason), "error");
          setNeedsReset(true);
          if (timerHandleRef.current) clearInterval(timerHandleRef.current);
        }
        if (!completedRef.current) { completedRef.current = true; onChallengeComplete(false, data.reason); }
      }
    } catch {
      onStatusChange("Verification error.", "error");
      if (!completedRef.current) { completedRef.current = true; onChallengeComplete(false, "error"); }
    }
  }, [challenge, onStatusChange, onTimerChange, onChallengeComplete]);

  const handlePointerDown = useCallback((evt: React.PointerEvent<HTMLCanvasElement>) => {
    evt.preventDefault();
    if (!challenge) return;
    if (solved) {
      onStatusChange("Passed. Click New Challenge.", "success");
      return;
    }
    if (needsReset) return;

    const now = Date.now();
    if (expired || now > challenge.expiresAt * 1000) {
      setExpired(true);
      onStatusChange("Too slow.", "error");
      return;
    }

    const profile = pointerProfileFromEvent(evt.nativeEvent);
    const start = challenge.startPoint;

    if (start) {
      const { x: offsetX, y: offsetY } = getCanvasCoords(evt);
      const dist = Math.hypot(offsetX - start[0], offsetY - start[1]);
      const tol = profile === "mouse" ? challenge.tolerance.mouse : challenge.tolerance.touch;
      const startRadius = tol * 1.25;

      if (dist > startRadius) {
        onStatusChange("Start on the blue dot.", "error");
        return;
      }

      const lineWidth = lineWidthForProfile(profile);
      const ts = performance.now();

      pointerProfileRef.current = profile;
      startTsRef.current = ts;
      drawingRef.current = true;
      trajectoryRef.current = [{ x: offsetX, y: offsetY, t: 0 }];
      segmentsRef.current = [{
        x: offsetX,
        y: offsetY,
        createdAt: ts,
        lineWidth,
      }];

      if (canvasRef.current) {
        canvasRef.current.setPointerCapture(evt.pointerId);
      }
    }
  }, [challenge, solved, needsReset, expired, onStatusChange]);

  const handlePointerMove = useCallback((evt: React.PointerEvent<HTMLCanvasElement>) => {
    evt.preventDefault();
    if (!drawingRef.current || !challenge) return;

    const { x: offsetX, y: offsetY } = getCanvasCoords(evt);
    const relT = performance.now() - startTsRef.current;

    const profile = pointerProfileRef.current;
    const lineWidth = lineWidthForProfile(profile);
    const deviation = distanceToPath(offsetX, offsetY, lookaheadRef.current);
    const tol = profile === "mouse" ? challenge.tolerance.mouse : challenge.tolerance.touch;

    // Push directly to refs — no setState, no re-render
    trajectoryRef.current.push({ x: offsetX, y: offsetY, t: Math.round(relT) });
    segmentsRef.current.push({
      x: offsetX,
      y: offsetY,
      createdAt: performance.now(),
      lineWidth,
      deviation,
      tolerance: tol,
    });

    if (finishPointRef.current) {
      distanceToEndRef.current = Math.hypot(
        offsetX - finishPointRef.current[0],
        offsetY - finishPointRef.current[1]
      );
    }

    // Real-time visual feedback via status color only
    if (deviation > tol * 1.5 && lookaheadRef.current.length > 0) {
      onStatusChange("", "error");
    } else {
      onStatusChange("", "success");
    }

    fetchPeek(offsetX, offsetY);
  }, [challenge, onStatusChange, fetchPeek]);

  const handlePointerUp = useCallback((evt: React.PointerEvent<HTMLCanvasElement>) => {
    evt.preventDefault();
    if (!drawingRef.current) return;

    if (canvasRef.current) {
      canvasRef.current.releasePointerCapture(evt.pointerId);
    }

    drawingRef.current = false;
    verifyAttemptHandler();
  }, [verifyAttemptHandler]);

  const handlePointerLeave = useCallback((evt: React.PointerEvent<HTMLCanvasElement>) => {
    if (drawingRef.current) {
      if (canvasRef.current) {
        canvasRef.current.releasePointerCapture(evt.pointerId);
      }
      drawingRef.current = false;
      setNeedsReset(true);
      if (timerHandleRef.current) clearInterval(timerHandleRef.current);
      onStatusChange("Strayed too far.", "error");
      if (!completedRef.current) { completedRef.current = true; onChallengeComplete(false, "low_coverage"); }
    }
  }, [onTimerChange, onStatusChange, onChallengeComplete]);

  // Animation loop — reads refs directly, no React dependency on pointer data
  useEffect(() => {
    let animationId: number;
    const tick = () => {
      drawFrame();
      animationId = requestAnimationFrame(tick);
    };
    animationId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(animationId);
    };
  }, [drawFrame]);

  return (
    <canvas
      ref={canvasRef}
      width={captchaConfig.canvasWidth}
      height={captchaConfig.canvasHeight}
      className="rounded-lg border-2 border-accent bg-muted/50 w-full h-full touch-none"
      aria-label="CAPTCHA challenge area"
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={handlePointerLeave}
      style={{
        aspectRatio: '1',
        maxWidth: '100%',
        height: 'auto',
      }}
    />
  );
}
