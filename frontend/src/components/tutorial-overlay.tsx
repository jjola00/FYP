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
  // Three lines creating two intersections:
  // Line A (pink):  (20,155) → (240,35)
  // Line B (blue):  (20,50)  → (150,145)
  // Line C (green): (140,25) → (240,155)
  // Intersection 1 (A∩B) ≈ (104, 102)
  // Intersection 2 (A∩C) ≈ (176, 69)

  const ix1 = { x: 104, y: 102 };
  const ix2 = { x: 176, y: 69 };

  // Cursor path: start off-canvas bottom-left, move to ix1, then ix2
  const cursorPath = `M40,160 L${ix1.x},${ix1.y} L${ix2.x},${ix2.y}`;

  // 4s loop: move→pause(click1)→move→pause(click2)→brief reset
  // keyPoints 0=start, 0.5=ix1, 1.0=ix2
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

      {/* Click effect at intersection 1 — ripple ring */}
      <circle cx={ix1.x} cy={ix1.y} r="6" fill="none" stroke="rgba(250,204,21,0.7)" strokeWidth="2">
        <animate attributeName="r" values="4;4;4;6;18;18;18;18;18;18" dur={dur} repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0;0;0.8;0;0;0;0;0;0" dur={dur} repeatCount="indefinite" />
      </circle>
      {/* Click dot that stays */}
      <circle cx={ix1.x} cy={ix1.y} r="0" fill="#FACC15">
        <animate attributeName="r" values="0;0;0;6;6;6;6;6;6;0" dur={dur} repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0;0;0.9;0.9;0.9;0.9;0.9;0.9;0" dur={dur} repeatCount="indefinite" />
      </circle>

      {/* Click effect at intersection 2 — ripple ring */}
      <circle cx={ix2.x} cy={ix2.y} r="6" fill="none" stroke="rgba(250,204,21,0.7)" strokeWidth="2">
        <animate attributeName="r" values="4;4;4;4;4;4;4;6;18;18" dur={dur} repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0;0;0;0;0;0;0.8;0;0" dur={dur} repeatCount="indefinite" />
      </circle>
      {/* Click dot that stays */}
      <circle cx={ix2.x} cy={ix2.y} r="0" fill="#FACC15">
        <animate attributeName="r" values="0;0;0;0;0;0;0;6;6;0" dur={dur} repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0;0;0;0;0;0;0.9;0.9;0" dur={dur} repeatCount="indefinite" />
      </circle>

      {/* Animated cursor that moves to each intersection and pauses */}
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

const TUTORIALS = {
  line: {
    title: "Trace the Path",
    description:
      "Press and hold the blue dot, then drag along the dashed line without lifting. The path reveals itself as you go.",
    Tutorial: LineTutorial,
  },
  visual: {
    title: "Spot the Crossings",
    description:
      "Tap or click where the coloured lines cross each other. Find all intersections, then hit Submit.",
    Tutorial: ImageTutorial,
  },
} as const;

export function TutorialOverlay({ type }: TutorialOverlayProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const key = STORAGE_KEYS[type];
    if (typeof window === "undefined") return;
    if (!localStorage.getItem(key)) {
      setOpen(true);
    }
  }, [type]);

  const handleDismiss = () => {
    localStorage.setItem(STORAGE_KEYS[type], "1");
    setOpen(false);
  };

  const { title, description, Tutorial } = TUTORIALS[type];

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleDismiss()}>
      <DialogContent className="max-w-xs sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <div className="py-2">
          <Tutorial />
        </div>
        <DialogFooter>
          <Button onClick={handleDismiss} className="w-full">
            Got it
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
