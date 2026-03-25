"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

export type CaptchaType = "line" | "visual";

// Group failure reasons into tutorial categories
type LineTutorialCategory = "incomplete" | "off_path" | "too_fast" | "timeout" | "natural";
type ImageTutorialCategory = "missed" | "excess" | "too_fast" | "timeout" | "general";

function getLineTutorialCategory(reason: string): LineTutorialCategory {
  switch (reason) {
    case "incomplete":
      return "incomplete";
    case "low_coverage":
    case "jump_detected":
    case "non_monotonic_path":
      return "off_path";
    case "too_fast":
    case "speed_violation":
      return "too_fast";
    case "timeout":
      return "timeout";
    default:
      return "natural";
  }
}

function getImageTutorialCategory(reason: string): ImageTutorialCategory {
  if (reason.startsWith("missed") || reason === "not all matched") return "missed";
  if (reason.startsWith("too many extra clicks") || reason === "excess clicks" || reason === "unexpected clicks") return "excess";
  if (reason === "solved too fast") return "too_fast";
  if (reason === "challenge expired") return "timeout";
  return "general";
}

// ── Line CAPTCHA tutorial animations ──────────────────────────────

function LineIncompleteTutorial() {
  return (
    <svg viewBox="0 0 260 160" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="160" rx="8" fill="#0a0f1d" />
      {/* Path */}
      <path d="M30,120 C80,120 100,40 180,50 C220,55 230,40 240,35"
        fill="none" stroke="rgba(129,140,248,0.4)" strokeWidth="3" strokeDasharray="4 3" />
      {/* Start dot */}
      <circle cx="30" cy="120" r="5" fill="rgba(56,189,248,1)" />
      {/* End dot (green, pulsing to draw attention) */}
      <circle cx="240" cy="35" r="7" fill="rgba(34,197,94,0.3)">
        <animate attributeName="r" values="6;9;6" dur="1.2s" repeatCount="indefinite" />
      </circle>
      <circle cx="240" cy="35" r="5" fill="rgba(34,197,94,0.9)" />
      {/* Cursor tracing all the way to the end */}
      <path d="M30,120 C80,120 100,40 180,50 C220,55 230,40 240,35"
        fill="none" stroke="rgba(56,189,248,0.7)" strokeWidth="4" strokeLinecap="round"
        strokeDasharray="300" strokeDashoffset="300">
        <animate attributeName="stroke-dashoffset" from="300" to="0" dur="2.5s" repeatCount="indefinite" />
      </path>
      {/* Cursor */}
      <circle r="5" fill="#FACC15" opacity="0.9">
        <animateMotion path="M30,120 C80,120 100,40 180,50 C220,55 230,40 240,35" dur="2.5s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

function LineOffPathTutorial() {
  return (
    <svg viewBox="0 0 260 160" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="160" rx="8" fill="#0a0f1d" />
      {/* Path with tolerance band */}
      <path d="M30,100 C90,100 110,40 180,60 C220,70 230,50 240,45"
        fill="none" stroke="rgba(129,140,248,0.15)" strokeWidth="24" strokeLinecap="round" />
      <path d="M30,100 C90,100 110,40 180,60 C220,70 230,50 240,45"
        fill="none" stroke="rgba(129,140,248,0.5)" strokeWidth="3" strokeDasharray="4 3" />
      <circle cx="30" cy="100" r="5" fill="rgba(56,189,248,1)" />
      <circle cx="240" cy="45" r="5" fill="rgba(34,197,94,0.9)" />
      {/* Cursor staying inside the band */}
      <path d="M30,100 C90,102 110,42 180,58 C220,68 230,48 240,45"
        fill="none" stroke="rgba(56,189,248,0.7)" strokeWidth="4" strokeLinecap="round"
        strokeDasharray="300" strokeDashoffset="300">
        <animate attributeName="stroke-dashoffset" from="300" to="0" dur="2.5s" repeatCount="indefinite" />
      </path>
      <circle r="5" fill="#FACC15" opacity="0.9">
        <animateMotion path="M30,100 C90,102 110,42 180,58 C220,68 230,48 240,45" dur="2.5s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

function LineTooFastTutorial() {
  return (
    <svg viewBox="0 0 260 160" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="160" rx="8" fill="#0a0f1d" />
      <path d="M30,110 C80,110 120,30 200,50 C230,55 240,45 245,40"
        fill="none" stroke="rgba(129,140,248,0.4)" strokeWidth="3" strokeDasharray="4 3" />
      <circle cx="30" cy="110" r="5" fill="rgba(56,189,248,1)" />
      <circle cx="245" cy="40" r="5" fill="rgba(34,197,94,0.9)" />
      {/* Slow, steady cursor (4s instead of 2.5s) */}
      <path d="M30,110 C80,110 120,30 200,50 C230,55 240,45 245,40"
        fill="none" stroke="rgba(56,189,248,0.7)" strokeWidth="4" strokeLinecap="round"
        strokeDasharray="300" strokeDashoffset="300">
        <animate attributeName="stroke-dashoffset" from="300" to="0" dur="4s" repeatCount="indefinite" />
      </path>
      <circle r="5" fill="#FACC15" opacity="0.9">
        <animateMotion path="M30,110 C80,110 120,30 200,50 C230,55 240,45 245,40" dur="4s" repeatCount="indefinite" />
      </circle>
      {/* Slow label */}
      <text x="130" y="145" textAnchor="middle" fill="rgba(250,204,21,0.7)" fontSize="11" fontFamily="sans-serif">
        steady pace
      </text>
    </svg>
  );
}

function LineTimeoutTutorial() {
  return (
    <svg viewBox="0 0 260 160" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="160" rx="8" fill="#0a0f1d" />
      <path d="M30,110 C80,110 120,30 200,50 C230,55 240,45 245,40"
        fill="none" stroke="rgba(129,140,248,0.4)" strokeWidth="3" strokeDasharray="4 3" />
      <circle cx="30" cy="110" r="5" fill="rgba(56,189,248,1)" />
      <circle cx="245" cy="40" r="5" fill="rgba(34,197,94,0.9)" />
      {/* Quick but controlled trace */}
      <path d="M30,110 C80,110 120,30 200,50 C230,55 240,45 245,40"
        fill="none" stroke="rgba(56,189,248,0.7)" strokeWidth="4" strokeLinecap="round"
        strokeDasharray="300" strokeDashoffset="300">
        <animate attributeName="stroke-dashoffset" from="300" to="0" dur="2s" repeatCount="indefinite" />
      </path>
      <circle r="5" fill="#FACC15" opacity="0.9">
        <animateMotion path="M30,110 C80,110 120,30 200,50 C230,55 240,45 245,40" dur="2s" repeatCount="indefinite" />
      </circle>
      {/* Timer icon */}
      <circle cx="230" cy="130" r="12" fill="none" stroke="rgba(239,68,68,0.6)" strokeWidth="2" />
      <line x1="230" y1="122" x2="230" y2="130" stroke="rgba(239,68,68,0.8)" strokeWidth="2" strokeLinecap="round">
        <animateTransform attributeName="transform" type="rotate" from="0 230 130" to="360 230 130" dur="2s" repeatCount="indefinite" />
      </line>
    </svg>
  );
}

function LineNaturalTutorial() {
  return (
    <svg viewBox="0 0 260 160" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="160" rx="8" fill="#0a0f1d" />
      <path d="M30,110 C70,110 90,35 150,55 C210,75 220,100 240,40"
        fill="none" stroke="rgba(129,140,248,0.4)" strokeWidth="3" strokeDasharray="4 3" />
      <circle cx="30" cy="110" r="5" fill="rgba(56,189,248,1)" />
      <circle cx="240" cy="40" r="5" fill="rgba(34,197,94,0.9)" />
      {/* Slightly wobbly, natural-looking trace */}
      <path d="M30,110 C72,112 88,37 150,57 C208,73 222,98 240,40"
        fill="none" stroke="rgba(56,189,248,0.7)" strokeWidth="4" strokeLinecap="round"
        strokeDasharray="300" strokeDashoffset="300">
        <animate attributeName="stroke-dashoffset" from="300" to="0" dur="3s" repeatCount="indefinite" />
      </path>
      <circle r="5" fill="#FACC15" opacity="0.9">
        <animateMotion path="M30,110 C72,112 88,37 150,57 C208,73 222,98 240,40" dur="3s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

// ── Image CAPTCHA tutorial animations ─────────────────────────────

function ImageMissedTutorial() {
  return (
    <svg viewBox="0 0 260 160" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="160" rx="8" fill="#0a0f1d" />
      {/* Two crossing lines */}
      <line x1="40" y1="130" x2="220" y2="20" stroke="#e879f9" strokeWidth="3" strokeLinecap="round" />
      <line x1="40" y1="30" x2="230" y2="120" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" />
      {/* Intersection highlight circle */}
      <circle cx="132" cy="75" r="16" fill="none" stroke="rgba(250,204,21,0.4)" strokeWidth="2" strokeDasharray="4 3">
        <animate attributeName="r" values="14;18;14" dur="1.5s" repeatCount="indefinite" />
      </circle>
      {/* Click cursor hitting the intersection */}
      <circle cx="132" cy="75" r="6" fill="rgba(250,204,21,0)" >
        <animate attributeName="fill" values="rgba(250,204,21,0);rgba(250,204,21,0);rgba(250,204,21,0.9);rgba(250,204,21,0.9);rgba(250,204,21,0)"
          dur="2s" repeatCount="indefinite" />
        <animate attributeName="r" values="0;0;6;8;0" dur="2s" repeatCount="indefinite" />
      </circle>
      {/* Click ring effect */}
      <circle cx="132" cy="75" r="6" fill="none" stroke="rgba(250,204,21,0.5)" strokeWidth="2">
        <animate attributeName="r" values="6;20;20" dur="2s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0.6;0" dur="2s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

function ImageExcessTutorial() {
  return (
    <svg viewBox="0 0 260 200" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="200" rx="8" fill="#0a0f1d" />

      {/* LEFT SIDE: valid intersection (lines actually cross) */}
      <text x="65" y="18" textAnchor="middle" fill="rgba(34,197,94,0.8)" fontSize="10" fontFamily="sans-serif">correct</text>
      <line x1="20" y1="90" x2="110" y2="30" stroke="#e879f9" strokeWidth="3" strokeLinecap="round" />
      <line x1="20" y1="35" x2="110" y2="85" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" />
      {/* Green check at intersection */}
      <circle cx="65" cy="60" r="10" fill="rgba(34,197,94,0.2)" stroke="rgba(34,197,94,0.6)" strokeWidth="1.5" />
      <circle cx="65" cy="60" r="4" fill="rgba(34,197,94,0.9)" />

      {/* Divider */}
      <line x1="130" y1="22" x2="130" y2="105" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />

      {/* RIGHT SIDE: lines close but NOT crossing */}
      <text x="195" y="18" textAnchor="middle" fill="rgba(239,68,68,0.8)" fontSize="10" fontFamily="sans-serif">not a crossing</text>
      {/* Two lines that come close but don't cross */}
      <line x1="150" y1="85" x2="240" y2="30" stroke="#e879f9" strokeWidth="3" strokeLinecap="round" />
      <line x1="155" y1="30" x2="235" y2="75" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" />
      {/* Red X where someone might mistakenly click */}
      <g opacity="0.8">
        <line x1="190" y1="48" x2="200" y2="58" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
        <line x1="200" y1="48" x2="190" y2="58" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
      </g>

      {/* BOTTOM: near-parallel / tangent example */}
      <text x="65" y="120" textAnchor="middle" fill="rgba(34,197,94,0.8)" fontSize="10" fontFamily="sans-serif">crossing</text>
      <text x="195" y="120" textAnchor="middle" fill="rgba(239,68,68,0.8)" fontSize="10" fontFamily="sans-serif">just close</text>

      {/* Left: actual crossing */}
      <line x1="20" y1="150" x2="110" y2="170" stroke="#fbbf24" strokeWidth="3" strokeLinecap="round" />
      <line x1="30" y1="175" x2="100" y2="140" stroke="#34d399" strokeWidth="3" strokeLinecap="round" />
      <circle cx="63" cy="158" r="10" fill="rgba(34,197,94,0.2)" stroke="rgba(34,197,94,0.6)" strokeWidth="1.5" />
      <circle cx="63" cy="158" r="4" fill="rgba(34,197,94,0.9)" />

      {/* Divider */}
      <line x1="130" y1="125" x2="130" y2="195" stroke="rgba(255,255,255,0.1)" strokeWidth="1" />

      {/* Right: lines running close/parallel but not touching */}
      <line x1="150" y1="150" x2="240" y2="155" stroke="#fbbf24" strokeWidth="3" strokeLinecap="round" />
      <line x1="150" y1="165" x2="240" y2="170" stroke="#34d399" strokeWidth="3" strokeLinecap="round" />
      <g opacity="0.8">
        <line x1="190" y1="153" x2="200" y2="163" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
        <line x1="200" y1="153" x2="190" y2="163" stroke="#ef4444" strokeWidth="2.5" strokeLinecap="round" />
      </g>
    </svg>
  );
}

function ImageTooFastTutorial() {
  return (
    <svg viewBox="0 0 260 160" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="160" rx="8" fill="#0a0f1d" />
      <line x1="40" y1="130" x2="220" y2="20" stroke="#e879f9" strokeWidth="3" strokeLinecap="round" />
      <line x1="40" y1="30" x2="230" y2="120" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" />
      {/* Eye scanning animation - a gaze indicator moving across */}
      <circle r="8" fill="none" stroke="rgba(250,204,21,0.4)" strokeWidth="1.5" strokeDasharray="3 2">
        <animateMotion path="M60,40 L200,80 L130,75" dur="3s" repeatCount="indefinite" />
      </circle>
      {/* Then click */}
      <circle cx="132" cy="75" r="6" fill="rgba(250,204,21,0)">
        <animate attributeName="fill" values="rgba(250,204,21,0);rgba(250,204,21,0);rgba(250,204,21,0);rgba(250,204,21,0.9);rgba(250,204,21,0.9)"
          dur="3s" repeatCount="indefinite" />
      </circle>
      <text x="130" y="145" textAnchor="middle" fill="rgba(250,204,21,0.7)" fontSize="11" fontFamily="sans-serif">
        look carefully, then click
      </text>
    </svg>
  );
}

function ImageGeneralTutorial() {
  return (
    <svg viewBox="0 0 260 160" className="mx-auto w-full max-w-[260px]" aria-hidden="true">
      <rect width="260" height="160" rx="8" fill="#0a0f1d" />
      <line x1="40" y1="130" x2="220" y2="20" stroke="#e879f9" strokeWidth="3" strokeLinecap="round" />
      <line x1="40" y1="30" x2="230" y2="120" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" />
      <circle cx="132" cy="75" r="12" fill="rgba(250,204,21,0.2)">
        <animate attributeName="r" values="8;14;8" dur="1.5s" repeatCount="indefinite" />
      </circle>
      <circle cx="132" cy="75" r="6" fill="#FACC15">
        <animate attributeName="r" values="5;7;5" dur="1.5s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

// ── Tutorial configs ──────────────────────────────────────────────

const LINE_TUTORIALS: Record<LineTutorialCategory, { title: string; description: string; Component: () => React.ReactElement }> = {
  incomplete: {
    title: "Reach the End",
    description: "Trace the path all the way to the green dot at the end. Don't lift your finger or release the mouse button until you reach it.",
    Component: LineIncompleteTutorial,
  },
  off_path: {
    title: "Stay on the Path",
    description: "Keep your cursor or finger close to the dashed line. The highlighted band shows the area you need to stay within.",
    Component: LineOffPathTutorial,
  },
  too_fast: {
    title: "Slow Down",
    description: "You're going too fast. Trace at a steady, comfortable pace — there's no rush.",
    Component: LineTooFastTutorial,
  },
  timeout: {
    title: "Beat the Clock",
    description: "You ran out of time. Start tracing right away and keep a steady pace to finish before the timer expires.",
    Component: LineTimeoutTutorial,
  },
  natural: {
    title: "Trace Naturally",
    description: "Move at a natural pace with slight variations in speed. It's okay to have small wobbles — just follow the path smoothly.",
    Component: LineNaturalTutorial,
  },
};

const IMAGE_TUTORIALS: Record<ImageTutorialCategory, { title: string; description: string; Component: () => React.ReactElement }> = {
  missed: {
    title: "Find All Intersections",
    description: "Click exactly where the coloured lines cross each other. Look carefully — make sure you find every crossing point.",
    Component: ImageMissedTutorial,
  },
  excess: {
    title: "Valid vs Invalid Crossings",
    description: "Only click where lines actually cross through each other. Lines that run close together or nearly touch are not intersections.",
    Component: ImageExcessTutorial,
  },
  too_fast: {
    title: "Take Your Time",
    description: "Look at the whole image first before clicking. Make sure you've identified all the crossing points.",
    Component: ImageTooFastTutorial,
  },
  timeout: {
    title: "Beat the Clock",
    description: "Find and click the intersections, then hit Submit before time runs out.",
    Component: ImageGeneralTutorial,
  },
  general: {
    title: "Spot the Crossings",
    description: "Tap or click where the coloured lines cross each other, then hit Submit. Find all intersections to pass.",
    Component: ImageGeneralTutorial,
  },
};

// ── Exported component ────────────────────────────────────────────

interface FailureTutorialProps {
  open: boolean;
  onDismiss: () => void;
  captchaType: CaptchaType;
  failureReason: string;
}

export function FailureTutorial({ open, onDismiss, captchaType, failureReason }: FailureTutorialProps) {
  const tutorial = captchaType === "line"
    ? LINE_TUTORIALS[getLineTutorialCategory(failureReason)]
    : IMAGE_TUTORIALS[getImageTutorialCategory(failureReason)];

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onDismiss()}>
      <DialogContent className="max-w-xs sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{tutorial.title}</DialogTitle>
          <DialogDescription>{tutorial.description}</DialogDescription>
        </DialogHeader>
        <div className="py-2">
          <tutorial.Component />
        </div>
        <DialogFooter>
          <Button onClick={onDismiss} className="w-full">
            Got it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
