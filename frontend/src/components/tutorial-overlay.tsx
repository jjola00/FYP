"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

interface TutorialOverlayProps {
  type: "line" | "visual";
}

const STORAGE_KEYS = {
  line: "tutorial_seen_line",
  visual: "tutorial_seen_image",
} as const;

function LineTutorial() {
  return (
    <svg
      viewBox="0 0 260 180"
      className="mx-auto w-full max-w-[260px]"
      aria-hidden="true"
    >
      {/* Background */}
      <rect width="260" height="180" rx="8" fill="#0a0f1d" />

      {/* Start dot */}
      <circle cx="30" cy="140" r="8" fill="rgba(56,189,248,0.25)" />
      <circle cx="30" cy="140" r="5" fill="rgba(56,189,248,1)" />

      {/* Curved path that progressively reveals */}
      <path
        d="M30,140 C70,140 80,40 140,60 C200,80 210,140 230,50"
        fill="none"
        stroke="rgba(129,140,248,0.9)"
        strokeWidth="3"
        strokeDasharray="4 3"
      >
        <animate
          attributeName="stroke-dashoffset"
          from="300"
          to="0"
          dur="3s"
          repeatCount="indefinite"
        />
      </path>

      {/* Trail drawn by cursor */}
      <path
        d="M30,140 C70,140 80,40 140,60 C200,80 210,140 230,50"
        fill="none"
        stroke="rgba(56,189,248,0.7)"
        strokeWidth="4"
        strokeLinecap="round"
        strokeDasharray="300"
        strokeDashoffset="300"
      >
        <animate
          attributeName="stroke-dashoffset"
          from="300"
          to="0"
          dur="3s"
          repeatCount="indefinite"
        />
      </path>

      {/* Animated cursor following the path */}
      <circle r="6" fill="#FACC15" opacity="0.9">
        <animateMotion
          path="M30,140 C70,140 80,40 140,60 C200,80 210,140 230,50"
          dur="3s"
          repeatCount="indefinite"
        />
      </circle>

      {/* End dot */}
      <circle cx="230" cy="50" r="6" fill="rgba(34,197,94,0.8)" />
    </svg>
  );
}

function ImageTutorial() {
  const ix1 = { x: 104, y: 102 };
  const ix2 = { x: 176, y: 69 };

  const cursorPath = `M40,160 L${ix1.x},${ix1.y} L${ix2.x},${ix2.y}`;

  const keyPoints = "0;0.5;0.5;1;1";
  const keyTimes = "0;0.22;0.42;0.68;1";
  const dur = "4s";

  return (
    <svg
      viewBox="0 0 260 180"
      className="mx-auto w-full max-w-[260px]"
      aria-hidden="true"
    >
      {/* Background */}
      <rect width="260" height="180" rx="8" fill="#0a0f1d" />

      {/* Three crossing lines */}
      <line x1="20" y1="155" x2="240" y2="35" stroke="#e879f9" strokeWidth="3" strokeLinecap="round" />
      <line x1="20" y1="50" x2="150" y2="145" stroke="#38bdf8" strokeWidth="3" strokeLinecap="round" />
      <line x1="140" y1="25" x2="240" y2="155" stroke="#34d399" strokeWidth="3" strokeLinecap="round" />

      {/* Click effect at intersection 1 */}
      <circle cx={ix1.x} cy={ix1.y} r="6" fill="none" stroke="rgba(250,204,21,0.7)" strokeWidth="2">
        <animate attributeName="r" values="4;4;4;6;18;18;18;18;18;18" dur={dur} repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0;0;0.8;0;0;0;0;0;0" dur={dur} repeatCount="indefinite" />
      </circle>
      <circle cx={ix1.x} cy={ix1.y} r="0" fill="#FACC15">
        <animate attributeName="r" values="0;0;0;6;6;6;6;6;6;0" dur={dur} repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0;0;0.9;0.9;0.9;0.9;0.9;0.9;0" dur={dur} repeatCount="indefinite" />
      </circle>

      {/* Click effect at intersection 2 */}
      <circle cx={ix2.x} cy={ix2.y} r="6" fill="none" stroke="rgba(250,204,21,0.7)" strokeWidth="2">
        <animate attributeName="r" values="4;4;4;4;4;4;4;6;18;18" dur={dur} repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0;0;0;0;0;0;0.8;0;0" dur={dur} repeatCount="indefinite" />
      </circle>
      <circle cx={ix2.x} cy={ix2.y} r="0" fill="#FACC15">
        <animate attributeName="r" values="0;0;0;0;0;0;0;6;6;0" dur={dur} repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0;0;0;0;0;0;0.9;0.9;0" dur={dur} repeatCount="indefinite" />
      </circle>

      {/* Animated cursor */}
      <circle r="6" fill="#FACC15" opacity="0.9">
        <animateMotion
          path={cursorPath}
          keyPoints={keyPoints}
          keyTimes={keyTimes}
          calcMode="linear"
          dur={dur}
          repeatCount="indefinite"
        />
      </circle>
    </svg>
  );
}

// ── Popup step definitions per CAPTCHA type ──────────────────────

interface PopupStep {
  title: string;
  description: string;
  content?: React.ComponentType;
}

const LINE_STEPS: PopupStep[] = [
  {
    title: "Trace the Path",
    description:
      "Press and hold the blue dot, then drag along the dashed line without lifting. The path reveals itself as you go.",
    content: LineTutorial,
  },
  {
    title: "Take Your Time",
    description:
      "Trace naturally — like you're following a line with your finger. You don't need to be super accurate. Just relax and move at a comfortable pace.",
  },
  {
    title: "Challenges Are Timed",
    description:
      "Each challenge has a countdown timer shown in the bottom-right corner. You have 20 seconds for this challenge",
  },
];

const IMAGE_STEPS: PopupStep[] = [
  {
    title: "Spot the Crossings",
    description:
      "Tap or click where the coloured lines cross each other. Find all intersections, then hit Submit.",
    content: ImageTutorial,
  },
  {
    title: "Challenges Are Timed",
    description:
      "Each challenge has a countdown timer shown in the bottom-right corner. You have 20 seconds for this challenge.",
  },
];

const STEPS_BY_TYPE = {
  line: LINE_STEPS,
  visual: IMAGE_STEPS,
} as const;

// ── Component ────────────────────────────────────────────────────

export function TutorialOverlay({ type }: TutorialOverlayProps) {
  const [stepIndex, setStepIndex] = useState(0);
  const [open, setOpen] = useState(false);

  const steps = STEPS_BY_TYPE[type];

  useEffect(() => {
    const key = STORAGE_KEYS[type];
    if (typeof window === "undefined") return;
    if (!localStorage.getItem(key)) {
      setStepIndex(0);
      setOpen(true);
    }
  }, [type]);

  const handleNext = () => {
    if (stepIndex < steps.length - 1) {
      setStepIndex((prev) => prev + 1);
    } else {
      // Final step — mark as seen and close
      localStorage.setItem(STORAGE_KEYS[type], "1");
      setOpen(false);
    }
  };

  const step = steps[stepIndex];
  const isLast = stepIndex === steps.length - 1;
  const Content = step?.content;

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) handleNext(); }}>
      <DialogContent className="max-w-xs sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{step?.title}</DialogTitle>
          <DialogDescription>{step?.description}</DialogDescription>
        </DialogHeader>
        {Content && (
          <div className="py-2">
            <Content />
          </div>
        )}
        <DialogFooter>
          <Button onClick={handleNext} className="w-full">
            {isLast ? "Got it" : "Next"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
