"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ThemeToggle } from "@/components/theme-toggle";
import { CaptchaCanvas } from "@/components/captcha-canvas";
import { ImageCaptchaCanvas } from "@/components/image-captcha-canvas";
import { FeedbackWidget } from "@/components/feedback-widget";
import {
  Challenge,
  ImageChallenge,
  fetchChallenge,
  fetchImageChallenge,
} from "@/lib/api";

const LINE_INSTRUCTION =
  "HOLD the blue dot and trace the line without lifting. The path appears as you go.";

const FALLBACK_AFTER_FAILURES = 3;

export default function CaptchaPage() {
  const [activeTab, setActiveTab] = useState<"line" | "visual">("line");
  const [instruction, setInstruction] = useState(LINE_INSTRUCTION);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [imageChallenge, setImageChallenge] = useState<ImageChallenge | null>(null);
  const [statusText, setStatusText] = useState("");
  const [statusTone, setStatusTone] = useState<"info" | "error" | "success">("info");
  const [timer, setTimer] = useState("Time: --");
  const [isLoading, setIsLoading] = useState(false);

  // ── Verified state (5.3) ──────────────────────────────────────
  const [verified, setVerified] = useState(false);
  const [verifiedType, setVerifiedType] = useState<"line" | "visual" | null>(null);

  // ── Failure tracking (5.4) ────────────────────────────────────
  const [lineFailures, setLineFailures] = useState(0);
  const [imageFailures, setImageFailures] = useState(0);

  // ── Mid-attempt reset (5.2) ───────────────────────────────────
  const [pendingTab, setPendingTab] = useState<"line" | "visual" | null>(null);
  const lineAttemptRef = useRef<() => boolean>(() => false);
  const imageAttemptRef = useRef<() => boolean>(() => false);

  const handleStatusChange = (newStatus: string, tone?: "info" | "error" | "success") => {
    setStatusText(newStatus);
    setStatusTone(tone || "info");
  };

  const handleTimerChange = (time: string) => {
    setTimer(time ? `Time: ${time}` : "Time: --");
  };

  const handleChallengeComplete = useCallback((success: boolean) => {
    if (success) {
      setVerified(true);
      setVerifiedType(activeTab);
      // Notify consuming applications
      window.dispatchEvent(
        new CustomEvent("captcha-verified", { detail: { type: activeTab } })
      );
      // Reset failure counters
      setLineFailures(0);
      setImageFailures(0);
    } else {
      // Increment failure counter for the active tab
      if (activeTab === "line") {
        setLineFailures((prev) => prev + 1);
      } else {
        setImageFailures((prev) => prev + 1);
      }
    }
  }, [activeTab]);

  const loadChallenge = async (tab: "line" | "visual") => {
    setIsLoading(true);
    setStatusText("");
    setStatusTone("info");
    setTimer("Time: --");

    try {
      if (tab === "line") {
        const newChallenge = await fetchChallenge();
        setChallenge(newChallenge);
        setInstruction(LINE_INSTRUCTION);
      } else {
        const newChallenge = await fetchImageChallenge();
        setImageChallenge(newChallenge);
        setInstruction(newChallenge.instruction);
      }
      setStatusText("");
      setStatusTone("info");
    } catch (error) {
      setStatusText("Failed to load");
      setStatusTone("error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChallenge = () => loadChallenge(activeTab);

  const switchToTab = (tab: "line" | "visual") => {
    setActiveTab(tab);
    // Reset failure counter for the tab we're leaving
    if (tab === "line") {
      setImageFailures(0);
    } else {
      setLineFailures(0);
    }
    loadChallenge(tab);
    setPendingTab(null);
  };

  const handleTabChange = (value: string) => {
    const tab = value as "line" | "visual";
    if (tab === activeTab) return;

    // Check if there's an attempt in progress
    const inProgress =
      activeTab === "line"
        ? lineAttemptRef.current()
        : imageAttemptRef.current();

    if (inProgress) {
      setPendingTab(tab);
    } else {
      switchToTab(tab);
    }
  };

  const handleResetVerified = () => {
    setVerified(false);
    setVerifiedType(null);
    loadChallenge(activeTab);
  };

  // Load initial challenge
  useEffect(() => {
    loadChallenge("line");
  }, []);

  // Derive nudge messages
  const showLineNudge = lineFailures >= FALLBACK_AFTER_FAILURES;
  const showImageNudge = imageFailures >= FALLBACK_AFTER_FAILURES;
  const showNudge =
    (activeTab === "line" && showLineNudge) ||
    (activeTab === "visual" && showImageNudge);
  const nudgeTarget = activeTab === "line" ? "visual" : "line";
  const nudgeLabel =
    nudgeTarget === "line" ? "Trace the Path" : "Spot the Crossings";

  // ── Verified banner ─────────────────────────────────────────
  if (verified) {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center p-2 sm:p-4">
        <Card className="w-full max-w-sm sm:max-w-md shadow-2xl shadow-primary/10">
          <CardHeader className="relative">
            <div className="absolute top-4 right-4 sm:top-6 sm:right-6">
              <ThemeToggle />
            </div>
            <CardTitle className="font-headline text-center text-lg font-bold text-primary sm:text-xl md:text-2xl">
              Beyond Recognition
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center gap-4 py-8">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-500/20">
                <svg
                  className="h-8 w-8 text-green-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={3}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
              </div>
              <p className="text-lg font-semibold text-green-500" role="status" aria-live="assertive">
                Verified
              </p>
              <p className="text-sm text-muted-foreground">
                You passed the{" "}
                {verifiedType === "line" ? "Trace the Path" : "Spot the Crossings"}{" "}
                challenge.
              </p>
              <Button variant="ghost" size="sm" onClick={handleResetVerified}>
                Reset
              </Button>
            </div>
          </CardContent>
        </Card>
        <FeedbackWidget />
      </main>
    );
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center p-2 sm:p-4">
      <Card className="w-full max-w-sm sm:max-w-md shadow-2xl shadow-primary/10">
        <CardHeader className="relative">
          <div className="absolute top-4 right-4 sm:top-6 sm:right-6">
            <ThemeToggle />
          </div>
          <CardTitle className="font-headline text-center text-lg font-bold text-primary sm:text-xl md:text-2xl">
            Beyond Recognition
          </CardTitle>
          <p className="text-center text-sm text-muted-foreground">
            Verify you&apos;re human — choose a challenge type
          </p>
        </CardHeader>
        <CardContent>
          <Tabs
            value={activeTab}
            className="w-full"
            onValueChange={handleTabChange}
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="line">Trace the Path</TabsTrigger>
              <TabsTrigger value="visual">Spot the Crossings</TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Mid-attempt switch warning (5.2) */}
          {pendingTab && (
            <div className="mt-3 flex items-center justify-between rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-sm">
              <span className="text-yellow-600 dark:text-yellow-400">
                You have an attempt in progress.
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="ml-2 text-yellow-600 dark:text-yellow-400 hover:text-yellow-700"
                onClick={() => switchToTab(pendingTab)}
              >
                Switch anyway?
              </Button>
            </div>
          )}

          <div className="mt-4 sm:mt-6 flex flex-col items-center gap-4">
            {activeTab === "line" ? (
              <div className="relative w-full max-w-[350px] aspect-square">
                {challenge ? (
                  <CaptchaCanvas
                    challenge={challenge}
                    onStatusChange={handleStatusChange}
                    onTimerChange={handleTimerChange}
                    onChallengeComplete={handleChallengeComplete}
                    isAttemptInProgressRef={lineAttemptRef}
                  />
                ) : (
                  <div className="rounded-lg border-2 border-accent bg-muted/50 w-full h-full flex items-center justify-center">
                    <p className="text-muted-foreground">Loading challenge...</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="relative w-full max-w-[350px]">
                {imageChallenge ? (
                  <ImageCaptchaCanvas
                    challenge={imageChallenge}
                    onStatusChange={handleStatusChange}
                    onTimerChange={handleTimerChange}
                    onChallengeComplete={handleChallengeComplete}
                    onRequestNew={() => loadChallenge("visual")}
                    isAttemptInProgressRef={imageAttemptRef}
                  />
                ) : (
                  <div className="rounded-lg border-2 border-accent bg-muted/50 w-full aspect-square flex items-center justify-center">
                    <p className="text-muted-foreground">Loading challenge...</p>
                  </div>
                )}
              </div>
            )}

            <p className="flex min-h-[3rem] items-center text-center text-sm text-muted-foreground sm:min-h-[2.5rem]">
              {instruction}
            </p>

            <div className="flex w-full items-center justify-between gap-4 border-t border-border pt-4">
              <Button
                variant="outline"
                onClick={handleNewChallenge}
                disabled={isLoading}
              >
                {isLoading ? "Loading..." : "New Challenge"}
              </Button>
              <div className="flex flex-col items-end">
                <p
                  className={`text-sm font-medium ${
                    statusTone === "success"
                      ? "text-green-500"
                      : statusTone === "error"
                        ? "text-red-400"
                        : "text-foreground"
                  }`}
                  role="status"
                  aria-live="polite"
                >
                  {statusText || "Status"}
                </p>
                <span aria-live="polite" aria-atomic="true">
                  <p className="font-mono text-sm text-primary">
                    {timer}
                  </p>
                </span>
              </div>
            </div>

            {/* Cross-type nudge (5.4) */}
            {showNudge && (
              <p className="text-sm text-muted-foreground">
                Having trouble?{" "}
                <button
                  className="text-primary underline hover:text-primary/80"
                  onClick={() => switchToTab(nudgeTarget)}
                >
                  Try {nudgeLabel} instead.
                </button>
              </p>
            )}
          </div>
        </CardContent>
      </Card>
      <FeedbackWidget />
    </main>
  );
}
