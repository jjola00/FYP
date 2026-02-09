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
}: ImageCaptchaCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [clicks, setClicks] = useState<ClickMarker[]>([]);
  const [expired, setExpired] = useState(false);
  const [solved, setSolved] = useState(false);
  const [submitted, setSubmitted] = useState(false);

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
      onTimerChange("");
      onStatusChange("", "info");
    }
  }, [challenge?.challengeId]);

  // ── Shared line drawing helper ────────────────────────────────
  const drawLine = useCallback(
    (ctx: CanvasRenderingContext2D, line: ImageLineDefinition) => {
      const pts = line.points;
      ctx.save();
      ctx.strokeStyle = line.colour;
      ctx.lineWidth = line.thickness;
      ctx.globalAlpha = line.opacity ?? 1.0;
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

    // Draw distractor shapes first (behind everything)
    for (const shape of challenge.shapes ?? []) {
      ctx.save();
      ctx.globalAlpha = shape.opacity;
      ctx.strokeStyle = shape.colour;
      ctx.lineWidth = shape.strokeWidth;

      if (shape.kind === "circle" && shape.radius != null) {
        ctx.beginPath();
        ctx.arc(shape.x, shape.y, shape.radius, 0, 2 * Math.PI);
        ctx.stroke();
      } else if (
        shape.kind === "rectangle" &&
        shape.width != null &&
        shape.height != null
      ) {
        ctx.strokeRect(shape.x, shape.y, shape.width, shape.height);
      }

      ctx.restore();
    }

    // Draw distractor lines (behind challenge lines, muted)
    for (const d of challenge.distractors ?? []) {
      drawLine(ctx, d);
    }

    // Draw challenge lines (full opacity)
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
  }, [challenge, clicks, drawLine]);

  // Redraw when challenge or clicks change
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

  // ── Click handler ─────────────────────────────────────────────
  const handlePointerDown = useCallback(
    (evt: React.PointerEvent<HTMLCanvasElement>) => {
      evt.preventDefault();
      if (!challenge || expired || solved || submitted) return;

      const now = Date.now();
      if (now > challenge.expiresAt * 1000) {
        setExpired(true);
        onStatusChange("Time's up.", "error");
        return;
      }

      const { x, y } = getCanvasCoords(evt);
      setClicks((prev) => [...prev, { x, y }]);
    },
    [challenge, expired, solved, submitted, onStatusChange]
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
      const result = await verifyImageAttempt(challenge, clicks);

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
      console.error("Image verification error:", err);
      onStatusChange("Verification error.", "error");
      onChallengeComplete(false);
    }
  }, [challenge, clicks, solved, submitted, onStatusChange, onChallengeComplete]);

  // ── Derived values ────────────────────────────────────────────
  const expected = challenge?.numIntersections ?? 0;
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
        className={`rounded-lg border-2 border-accent bg-muted/50 w-full touch-none ${
          interactionDisabled ? "opacity-80" : "cursor-crosshair"
        }`}
        aria-label="Image CAPTCHA - click on line intersection points"
        onPointerDown={handlePointerDown}
        onContextMenu={(e) => e.preventDefault()}
        style={{ aspectRatio: "1", maxWidth: "100%", height: "auto" }}
      />

      {/* Click counter dots */}
      <div
        className="flex items-center gap-1.5"
        aria-label={`${placed} of ${expected} clicks placed`}
      >
        <span className="text-xs text-muted-foreground mr-1">Clicks:</span>
        {Array.from({ length: expected }).map((_, i) => (
          <span
            key={i}
            className={`inline-block w-2.5 h-2.5 rounded-full border ${
              i < placed
                ? "bg-yellow-400 border-yellow-500"
                : "bg-transparent border-muted-foreground/40"
            }`}
          />
        ))}
        {placed > expected && (
          <span className="text-xs text-orange-400 ml-1">+{placed - expected}</span>
        )}
      </div>

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

      {/* Refresh link */}
      {!solved && (
        <button
          className="text-xs text-muted-foreground hover:text-foreground underline"
          onClick={onRequestNew}
        >
          Can&apos;t see it? Request new challenge
        </button>
      )}
    </div>
  );
}
