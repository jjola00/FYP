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
  onChallengeComplete: (success: boolean) => void;
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
  const [state, setState] = useState({
    drawing: false,
    expired: false,
    solved: false,
    needsReset: false,
    startTs: 0,
    trajectory: [] as TrajectoryPoint[],
    segments: [] as CanvasSegment[],
    pointerProfile: "mouse" as "mouse" | "touch",
    lookahead: [] as [number, number][],
    lastPeekAt: 0,
    peekMinIntervalMs: 100,
    peekBlockedUntil: 0,
    finishPoint: null as [number, number] | null,
    showFinish: false,
    devicePixelRatio: (typeof window !== 'undefined' ? window.devicePixelRatio : 1) || 1,
    distanceToEnd: null as number | null,
    timerHandle: null as NodeJS.Timeout | null,
    expiresAtMs: 0,
  });

  // Timer effect
  useEffect(() => {
    if (!challenge) return;
    
    setState(prev => ({ ...prev, expiresAtMs: challenge.expiresAt * 1000 }));
    
    const timerHandle = setInterval(() => {
      if (state.solved || state.needsReset) {
        clearInterval(timerHandle);
        return;
      }
      
      const now = Date.now();
      const remaining = Math.max(0, challenge.expiresAt * 1000 - now);
      onTimerChange(remaining ? `${Math.ceil(remaining / 1000)}s` : "");
      
      if (remaining <= 0) {
        setState(prev => ({ 
          ...prev, 
          expired: true, 
          drawing: false, 
          needsReset: true 
        }));
        onStatusChange("Too slow.", "error");
        clearInterval(timerHandle);
      }
    }, 200);
    
    setState(prev => ({ ...prev, timerHandle }));
    
    return () => {
      clearInterval(timerHandle);
    };
  }, [challenge, state.solved, state.needsReset]);

  // Reset state when challenge changes
  useEffect(() => {
    if (challenge) {
      setState(prev => ({
        ...prev,
        drawing: false,
        expired: false,
        solved: false,
        needsReset: false,
        trajectory: [],
        segments: [],
        lookahead: [],
        finishPoint: null,
        showFinish: false,
        distanceToEnd: null,
      }));
      onTimerChange("");
      if (state.timerHandle) {
        clearInterval(state.timerHandle);
      }
      // Prime lookahead at start point
      fetchLookahead(challenge, challenge.startPoint[0], challenge.startPoint[1])
        .then(data => {
          setState(prev => ({
            ...prev,
            lookahead: data.ahead,
            distanceToEnd: data.distanceToEnd,
            showFinish: Boolean(data.finish),
            finishPoint: data.finish || null,
          }));
        })
        .catch(() => {});
    }
  }, [challenge?.challengeId]);

  // Expose attempt-in-progress check to parent
  useEffect(() => {
    if (isAttemptInProgressRef) {
      isAttemptInProgressRef.current = () =>
        (state.drawing || state.trajectory.length > 0) &&
        !state.solved &&
        !state.needsReset;
    }
  }, [isAttemptInProgressRef, state.drawing, state.trajectory.length, state.solved, state.needsReset]);

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
    const dpr = state.devicePixelRatio || 1;
    if (profile === "mouse") {
      const base = tol?.mouse ? Math.max(3, Math.min(8, tol.mouse * 0.4)) : captchaConfig.lineWidthMouse;
      return base * (dpr >= 2 ? 1.15 : 1);
    }
    const base = tol?.touch ? Math.max(6, Math.min(10, tol.touch * 0.35)) : captchaConfig.lineWidthTouch;
    return base * (dpr >= 2 ? 1.15 : 1);
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

  const clearCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    // Use dark background instead of transparent
    ctx.fillStyle = "#0a0f1d";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }, []);

  const drawGuideLine = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !state.lookahead.length) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.save();
    ctx.strokeStyle = "rgba(129, 140, 248, 0.9)";
    ctx.lineWidth = 3.5;
    ctx.setLineDash([10, 5]);
    ctx.beginPath();
    ctx.moveTo(state.lookahead[0][0], state.lookahead[0][1]);
    for (let i = 1; i < state.lookahead.length; i++) {
      ctx.lineTo(state.lookahead[i][0], state.lookahead[i][1]);
    }
    ctx.stroke();
    ctx.restore();
  }, [state.lookahead]);

  const drawMarkers = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !challenge) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.save();
    // Draw start marker (bright + pulsing-like glow)
    const start = challenge.startPoint;
    ctx.fillStyle = "rgba(56, 189, 248, 0.25)";
    ctx.beginPath();
    ctx.arc(start[0], start[1], 16, 0, 2 * Math.PI);
    ctx.fill();
    ctx.fillStyle = "rgba(56, 189, 248, 1.0)";
    ctx.beginPath();
    ctx.arc(start[0], start[1], 10, 0, 2 * Math.PI);
    ctx.fill();

    // Draw finish marker if visible
    if (state.showFinish && state.finishPoint) {
      ctx.fillStyle = "rgba(34, 197, 94, 0.8)";
      ctx.beginPath();
      ctx.arc(state.finishPoint[0], state.finishPoint[1], 8, 0, 2 * Math.PI);
      ctx.fill();
    }
    ctx.restore();
  }, [challenge, state.showFinish, state.finishPoint]);

  const drawSegments = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || state.segments.length < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const now = performance.now();
    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    for (let i = 1; i < state.segments.length; i++) {
      const prev = state.segments[i - 1];
      const curr = state.segments[i];
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
  }, [state.segments]);

  const drawFrame = useCallback(() => {
    clearCanvas();
    drawGuideLine();
    drawMarkers();
    drawSegments();
  }, [clearCanvas, drawGuideLine, drawMarkers, drawSegments]);

  const verifyAttemptHandler = useCallback(async () => {
    if (!challenge || state.trajectory.length < 2) return;
    
    if (state.trajectory.length < captchaConfig.minSamples) {
      onStatusChange("Captcha incompleted.", "error");
      setState(prev => ({ ...prev, needsReset: true }));
      if (state.timerHandle) clearInterval(state.timerHandle);
      onTimerChange("");
      return;
    }

    onStatusChange("Verifying...");
    try {
      const trajectoryHash = await computeTrajectoryHash(
        state.trajectory,
        challenge.nonce,
        challenge.challengeId
      );
      const clientTimingMs = performance.now() - state.startTs;

      const data = await verifyAttempt(
        challenge,
        state.trajectory,
        state.pointerProfile,
        clientTimingMs,
        trajectoryHash
      );

      if (data.passed) {
        setState(prev => ({ ...prev, solved: true }));
        if (state.timerHandle) clearInterval(state.timerHandle);
        onTimerChange("");
        onStatusChange("Passed.", "success");
        onChallengeComplete(true);
      } else {
        if (data.reason === "timeout") {
          setState(prev => ({ 
            ...prev, 
            expired: true, 
            needsReset: true 
          }));
          if (state.timerHandle) clearInterval(state.timerHandle);
          onStatusChange("Too slow.", "error");
        } else {
          onStatusChange(formatFailureReason(data.reason), "error");
          setState(prev => ({ ...prev, needsReset: true }));
          if (state.timerHandle) clearInterval(state.timerHandle);
          onTimerChange("");
        }
        onChallengeComplete(false);
      }
    } catch (err) {
      onStatusChange("Verification error.", "error");
      onChallengeComplete(false);
    }
  }, [challenge, state.trajectory, state.startTs, state.pointerProfile, state.timerHandle, onStatusChange, onTimerChange, onChallengeComplete]);

  const fetchLookaheadHandler = useCallback(async (x: number, y: number, force = false) => {
    const now = performance.now();
    if (!force && now < state.peekBlockedUntil) return;
    if (!force && now - state.lastPeekAt < state.peekMinIntervalMs) return;
    
    setState(prev => ({ ...prev, lastPeekAt: now }));
    if (!challenge) return;
    
    try {
      const data = await fetchLookahead(challenge, x, y);
      setState(prev => ({
        ...prev,
        lookahead: data.ahead,
        distanceToEnd: data.distanceToEnd,
        showFinish: Boolean(data.finish),
        finishPoint: data.finish || null,
        peekMinIntervalMs: Math.max(100, prev.peekMinIntervalMs - 5),
      }));
    } catch (err: any) {
      if (err.message.includes("429")) {
        setState(prev => ({
          ...prev,
          peekMinIntervalMs: Math.min(250, prev.peekMinIntervalMs + 25),
          peekBlockedUntil: now + prev.peekMinIntervalMs,
        }));
      }
    }
  }, [challenge, state.peekBlockedUntil, state.lastPeekAt, state.peekMinIntervalMs]);

  const handlePointerDown = useCallback((evt: React.PointerEvent<HTMLCanvasElement>) => {
    evt.preventDefault();
    if (!challenge) return;
    if (state.solved) {
      onStatusChange("Passed. Click New Challenge.", "success");
      return;
    }
    if (state.needsReset) return;
    
    const now = Date.now();
    if (state.expired || now > challenge.expiresAt * 1000) {
      setState(prev => ({ ...prev, expired: true }));
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
      const startTs = performance.now();
      
      setState(prev => ({
        ...prev,
        drawing: true,
        startTs,
        trajectory: [{ x: offsetX, y: offsetY, t: 0 }],
        segments: [{
          x: offsetX,
          y: offsetY,
          createdAt: performance.now(),
          lineWidth,
        }],
        pointerProfile: profile,
      }));
      
      if (canvasRef.current) {
        canvasRef.current.setPointerCapture(evt.pointerId);
      }
    }
  }, [challenge, state.solved, state.needsReset, state.expired, onStatusChange]);

  const handlePointerMove = useCallback((evt: React.PointerEvent<HTMLCanvasElement>) => {
    evt.preventDefault();
    if (!state.drawing || !challenge) return;

    const { x: offsetX, y: offsetY } = getCanvasCoords(evt);
    const relT = performance.now() - state.startTs;
    
    const profile = state.pointerProfile;
    const lineWidth = lineWidthForProfile(profile);
    const deviation = distanceToPath(offsetX, offsetY, state.lookahead);
    const tol = profile === "mouse" ? challenge.tolerance.mouse : challenge.tolerance.touch;

    setState(prev => ({
      ...prev,
      trajectory: [...prev.trajectory, { x: offsetX, y: offsetY, t: Math.round(relT) }],
      segments: [...prev.segments, {
        x: offsetX,
        y: offsetY,
        createdAt: performance.now(),
        lineWidth,
        deviation,
        tolerance: tol,
      }],
      distanceToEnd: state.finishPoint ? 
        Math.hypot(offsetX - state.finishPoint[0], offsetY - state.finishPoint[1]) : 
        null,
    }));

    // Real-time visual feedback via status color only
    if (deviation > tol * 1.5 && state.lookahead.length > 0) {
      onStatusChange("", "error");
    } else {
      onStatusChange("", "success");
    }

    fetchLookaheadHandler(offsetX, offsetY);
  }, [state.drawing, state.startTs, state.pointerProfile, state.lookahead, state.finishPoint, state.distanceToEnd, challenge, onStatusChange, fetchLookaheadHandler]);

  const handlePointerUp = useCallback((evt: React.PointerEvent<HTMLCanvasElement>) => {
    evt.preventDefault();
    if (!state.drawing) return;
    
    if (canvasRef.current) {
      canvasRef.current.releasePointerCapture(evt.pointerId);
    }
    
    setState(prev => ({ ...prev, drawing: false }));
    verifyAttemptHandler();
  }, [state.drawing, verifyAttemptHandler]);

  const handlePointerLeave = useCallback((evt: React.PointerEvent<HTMLCanvasElement>) => {
    if (state.drawing) {
      if (canvasRef.current) {
        canvasRef.current.releasePointerCapture(evt.pointerId);
      }
      setState(prev => ({ 
        ...prev, 
        drawing: false, 
        needsReset: true 
      }));
      if (state.timerHandle) clearInterval(state.timerHandle);
      onTimerChange("");
      onStatusChange("Strayed too far.", "error");
    }
  }, [state.drawing, state.timerHandle, onTimerChange, onStatusChange]);

  // Animation loop
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