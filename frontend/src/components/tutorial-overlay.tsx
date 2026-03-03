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
  return (
    <svg
      viewBox="0 0 260 180"
      className="mx-auto w-full max-w-[260px]"
      aria-hidden="true"
    >
      {/* Background */}
      <rect width="260" height="180" rx="8" fill="#0a0f1d" />

      {/* Two crossing lines */}
      <line
        x1="40"
        y1="150"
        x2="220"
        y2="30"
        stroke="#e879f9"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <line
        x1="40"
        y1="40"
        x2="230"
        y2="140"
        stroke="#38bdf8"
        strokeWidth="3"
        strokeLinecap="round"
      />

      {/* Intersection marker — pulsing click */}
      <circle cx="132" cy="88" r="12" fill="rgba(250,204,21,0.2)">
        <animate
          attributeName="r"
          values="8;14;8"
          dur="1.5s"
          repeatCount="indefinite"
        />
        <animate
          attributeName="opacity"
          values="0.4;0.15;0.4"
          dur="1.5s"
          repeatCount="indefinite"
        />
      </circle>
      <circle cx="132" cy="88" r="6" fill="#FACC15">
        <animate
          attributeName="r"
          values="5;7;5"
          dur="1.5s"
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
