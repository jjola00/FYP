"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  captchaConfig,
  ImageChallenge,
  ImageLineDefinition,
  verifyImageAttempt,
} from "@/lib/api";

interface ImageCaptchaCanvasProps {
  challenge: ImageChallenge | null;
  onStatusChange: (status: string, tone?: "info" | "error" | "success") => void;
  onTimerChange: (time: string) => void;
  onChallengeComplete: (success: boolean) => void;
  onRequestNew: () => void;
  isAttemptInProgressRef?: React.MutableRefObject<() => boolean>;
}

interface ClickMarker {
  x: number;
  y: number;
}

export function ImageCaptchaCanvas({
  challenge,
  onStatusChange,
  onTimerChange,
  onChallengeComplete,
  onRequestNew,
  isAttemptInProgressRef,
}: ImageCaptchaCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pointerTypeRef = useRef<"mouse" | "touch">("mouse");
  const [clicks, setClicks] = useState<ClickMarker[]>([]);
  const [expired, setExpired] = useState(false);
  const [solved, setSolved] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // ── Keyboard cursor (5.5) ──────────────────────────────────────
  const [keyboardCursor, setKeyboardCursor] = useState<{ x: number; y: number } | null>(null);

  // ── Timer ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!challenge) return;

    const handle = setInterval(() => {
      if (solved || submitted) {
        clearInterval(handle);
        return;
      }

      const now = Date.now();
      const remaining = Math.max(0, challenge.expiresAt * 1000 - now);
      onTimerChange(remaining ? `${Math.ceil(remaining / 1000)}s` : "");

      if (remaining <= 0) {
        setExpired(true);
        onStatusChange("Time's up.", "error");
        clearInterval(handle);
      }
    }, 200);

    return () => clearInterval(handle);
  }, [challenge, solved, submitted, onStatusChange, onTimerChange]);

  // ── Reset on new challenge ────────────────────────────────────
  useEffect(() => {
    if (challenge) {
      setClicks([]);
      setExpired(false);
      setSolved(false);
      setSubmitted(false);
      setKeyboardCursor(null);
      onTimerChange("");
      onStatusChange("", "info");
    }
  }, [challenge?.challengeId]);

  // Expose attempt-in-progress check to parent
  useEffect(() => {
    if (isAttemptInProgressRef) {
      isAttemptInProgressRef.current = () =>
        clicks.length > 0 && !solved && !submitted;
    }
  }, [isAttemptInProgressRef, clicks.length, solved, submitted]);

  // ── Shared line drawing helper ────────────────────────────────
  const drawLine = useCallback(
    (ctx: CanvasRenderingContext2D, line: ImageLineDefinition) => {
      const pts = line.points;
      ctx.save();
      ctx.strokeStyle = line.colour;
      ctx.lineWidth = line.thickness;
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);

      switch (line.type) {
        case "straight":
          ctx.lineTo(pts[1][0], pts[1][1]);
          break;
        case "quadratic":
          ctx.quadraticCurveTo(
            pts[1][0], pts[1][1],
            pts[2][0], pts[2][1]
          );
          break;
        case "cubic":
          ctx.bezierCurveTo(
            pts[1][0], pts[1][1],
            pts[2][0], pts[2][1],
            pts[3][0], pts[3][1]
          );
          break;
      }

      ctx.stroke();
      ctx.restore();
    },
    []
  );

  // ── Canvas drawing ────────────────────────────────────────────
  const drawFrame = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !challenge) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const w = challenge.canvas.width;
    const h = challenge.canvas.height;

    // Dark background (matches line CAPTCHA style)
    ctx.fillStyle = "#0a0f1d";
    ctx.fillRect(0, 0, w, h);

    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Draw challenge lines
    for (const line of challenge.lines) {
      drawLine(ctx, line);
    }

    // Draw click markers (yellow with dark border, per architecture doc)
    for (const click of clicks) {
      ctx.save();

      // Dark border
      ctx.beginPath();
      ctx.arc(click.x, click.y, 8, 0, 2 * Math.PI);
      ctx.fillStyle = "#1a1a2e";
      ctx.fill();

      // Yellow fill
      ctx.beginPath();
      ctx.arc(click.x, click.y, 6, 0, 2 * Math.PI);
      ctx.fillStyle = "#FACC15";
      ctx.fill();

      ctx.restore();
    }

    // Draw keyboard cursor crosshair (5.5)
    if (keyboardCursor) {
      ctx.save();
      ctx.strokeStyle = "#FACC15";
      ctx.lineWidth = 1.5;
      ctx.globalAlpha = 0.9;
      const arm = 12;
      const gap = 4;
      // Horizontal arms
      ctx.beginPath();
      ctx.moveTo(keyboardCursor.x - arm, keyboardCursor.y);
      ctx.lineTo(keyboardCursor.x - gap, keyboardCursor.y);
      ctx.moveTo(keyboardCursor.x + gap, keyboardCursor.y);
      ctx.lineTo(keyboardCursor.x + arm, keyboardCursor.y);
      // Vertical arms
      ctx.moveTo(keyboardCursor.x, keyboardCursor.y - arm);
      ctx.lineTo(keyboardCursor.x, keyboardCursor.y - gap);
      ctx.moveTo(keyboardCursor.x, keyboardCursor.y + gap);
      ctx.lineTo(keyboardCursor.x, keyboardCursor.y + arm);
      ctx.stroke();
      ctx.restore();
    }
  }, [challenge, clicks, drawLine, keyboardCursor]);

  // Redraw when challenge, clicks, or keyboard cursor changes
  useEffect(() => {
    drawFrame();
  }, [drawFrame]);

  // ── Coordinate conversion (same pattern as captcha-canvas.tsx) ─
  const getCanvasCoords = (
    evt: React.PointerEvent<HTMLCanvasElement>
  ): { x: number; y: number } => {
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

  // ── Place click at position (shared by pointer and keyboard) ──
  const placeClick = useCallback(
    (x: number, y: number) => {
      if (!challenge || expired || solved || submitted) return;

      const now = Date.now();
      if (now > challenge.expiresAt * 1000) {
        setExpired(true);
        onStatusChange("Time's up.", "error");
        return;
      }

      setClicks((prev) => [...prev, { x, y }]);
    },
    [challenge, expired, solved, submitted, onStatusChange]
  );

  // ── Click handler ─────────────────────────────────────────────
  const handlePointerDown = useCallback(
    (evt: React.PointerEvent<HTMLCanvasElement>) => {
      evt.preventDefault();
      pointerTypeRef.current = evt.pointerType === "mouse" ? "mouse" : "touch";
      const { x, y } = getCanvasCoords(evt);
      placeClick(x, y);
    },
    [placeClick]
  );

  // ── Undo last click ──────────────────────────────────────────
  const handleUndo = useCallback(() => {
    if (clicks.length === 0 || solved || submitted) return;
    setClicks((prev) => prev.slice(0, -1));
  }, [clicks.length, solved, submitted]);

  // ── Submit ────────────────────────────────────────────────────
  const handleSubmit = useCallback(async () => {
    if (!challenge || clicks.length === 0 || solved || submitted) return;

    setSubmitted(true);
    onStatusChange("Verifying...");

    try {
      const result = await verifyImageAttempt(challenge, clicks, pointerTypeRef.current);

      if (result.passed) {
        setSolved(true);
        onStatusChange("Passed.", "success");
        onChallengeComplete(true);
      } else {
        let msg: string;
        if (result.reason === "challenge expired") {
          setExpired(true);
          msg = "Time's up.";
        } else if (result.reason === "solved too fast") {
          msg = "Too fast. Try again.";
        } else if (result.reason.startsWith("missed")) {
          const n = result.expected - result.matched;
          msg = n === 1
            ? "Missed an intersection. Try again."
            : `Missed ${n} intersections. Try again.`;
        } else if (result.reason === "too many extra clicks") {
          msg = "Too many extra clicks. Try again.";
        } else {
          msg = "Not quite right. Try again.";
        }
        onStatusChange(msg, "error");
        onChallengeComplete(false);
      }
    } catch (err) {
      onStatusChange("Verification error.", "error");
      onChallengeComplete(false);
    }
  }, [challenge, clicks, solved, submitted, onStatusChange, onChallengeComplete]);

  // ── Keyboard navigation (5.5) ────────────────────────────────
  const handleCanvasFocus = useCallback(() => {
    if (!keyboardCursor && challenge) {
      const cx = Math.round(challenge.canvas.width / 2);
      const cy = Math.round(challenge.canvas.height / 2);
      setKeyboardCursor({ x: cx, y: cy });
    }
  }, [keyboardCursor, challenge]);

  const handleKeyDown = useCallback(
    (evt: React.KeyboardEvent<HTMLCanvasElement>) => {
      if (!challenge) return;
      const w = challenge.canvas.width;
      const h = challenge.canvas.height;
      const step = evt.shiftKey ? 1 : 5;

      switch (evt.key) {
        case "ArrowUp":
          evt.preventDefault();
          setKeyboardCursor((prev) => {
            const cur = prev ?? { x: w / 2, y: h / 2 };
            return { x: cur.x, y: Math.max(0, cur.y - step) };
          });
          break;
        case "ArrowDown":
          evt.preventDefault();
          setKeyboardCursor((prev) => {
            const cur = prev ?? { x: w / 2, y: h / 2 };
            return { x: cur.x, y: Math.min(h, cur.y + step) };
          });
          break;
        case "ArrowLeft":
          evt.preventDefault();
          setKeyboardCursor((prev) => {
            const cur = prev ?? { x: w / 2, y: h / 2 };
            return { x: Math.max(0, cur.x - step), y: cur.y };
          });
          break;
        case "ArrowRight":
          evt.preventDefault();
          setKeyboardCursor((prev) => {
            const cur = prev ?? { x: w / 2, y: h / 2 };
            return { x: Math.min(w, cur.x + step), y: cur.y };
          });
          break;
        case "Enter":
        case " ":
          evt.preventDefault();
          if (keyboardCursor) {
            placeClick(keyboardCursor.x, keyboardCursor.y);
          }
          break;
        case "Backspace":
          evt.preventDefault();
          handleUndo();
          break;
        case "Escape":
          evt.preventDefault();
          onRequestNew();
          break;
      }
    },
    [challenge, keyboardCursor, placeClick, handleUndo, onRequestNew]
  );

  // ── Derived values ────────────────────────────────────────────
  const placed = clicks.length;
  const canvasW = challenge?.canvas.width ?? captchaConfig.canvasWidth;
  const canvasH = challenge?.canvas.height ?? captchaConfig.canvasHeight;
  const interactionDisabled = expired || solved || submitted;

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={canvasW}
        height={canvasH}
        tabIndex={0}
        className={`rounded-lg border-2 border-accent bg-muted/50 w-full touch-none outline-none focus:ring-2 focus:ring-primary/50 ${
          interactionDisabled ? "opacity-80" : "cursor-crosshair"
        }`}
        aria-label="Image CAPTCHA canvas — click on line intersection points"
        onPointerDown={handlePointerDown}
        onContextMenu={(e) => e.preventDefault()}
        onFocus={handleCanvasFocus}
        onKeyDown={handleKeyDown}
        style={{ aspectRatio: "1", maxWidth: "100%", height: "auto" }}
      />

      {/* Undo / Submit buttons */}
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleUndo}
          disabled={placed === 0 || interactionDisabled}
        >
          Undo Last
        </Button>
        <Button
          size="sm"
          onClick={handleSubmit}
          disabled={placed === 0 || interactionDisabled}
        >
          Submit
        </Button>
      </div>
    </div>
  );
}
