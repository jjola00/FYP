"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
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
import { TutorialOverlay } from "@/components/tutorial-overlay";
import {
  Challenge,
  ImageChallenge,
  fetchChallenge,
  fetchImageChallenge,
} from "@/lib/api";
import { useConfetti } from "@/hooks/use-confetti";
import { FailureTutorial } from "@/components/failure-tutorial";

const LINE_INSTRUCTION =
  "HOLD the blue dot and trace the line without lifting. The path appears as you go.";

const CONSECUTIVE_FAILURE_NUDGE = 3;
const REQUIRED_ATTEMPTS = 5;
const AUTO_ADVANCE_DELAY_MS = 1800;

function AttemptDots({
  attempts,
  passes,
  total,
}: {
  attempts: number;
  passes: number;
  total: number;
}) {
  // Show dots for completed attempts: green=pass, red=fail, grey=remaining
  return (
    <div className="flex items-center gap-1.5">
      {Array.from({ length: total }, (_, i) => {
        let colorClass = "bg-muted-foreground/25"; // not yet attempted
        if (i < attempts) {
          // This attempt happened — but we only know total passes/attempts,
          // not per-attempt results. Show filled dots for attempts done.
          // We'll use a simpler approach: green for passes, red for fails, grey for remaining.
          // Since we don't track order, show passes first then fails.
          if (i < passes) {
            colorClass = "bg-green-500 scale-110";
          } else {
            colorClass = "bg-red-400 scale-110";
          }
        }
        return (
          <div
            key={i}
            className={`h-2.5 w-2.5 rounded-full transition-all duration-500 ${colorClass}`}
          />
        );
      })}
    </div>
  );
}

export default function CaptchaPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  const [activeTab, setActiveTab] = useState<"line" | "visual">("line");
  const [instruction, setInstruction] = useState(LINE_INSTRUCTION);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [imageChallenge, setImageChallenge] = useState<ImageChallenge | null>(null);
  const [statusText, setStatusText] = useState("");
  const [statusTone, setStatusTone] = useState<"info" | "error" | "success">("info");
  const [timer, setTimer] = useState("Time: --");
  const [isLoading, setIsLoading] = useState(false);

  // ── Confetti ────────────────────────────────────────────────────
  const { fireConfetti } = useConfetti();

  // ── Failure tutorial popup ──────────────────────────────────────
  const [failureTutorialOpen, setFailureTutorialOpen] = useState(false);
  const [failureReason, setFailureReason] = useState("");
  const [failureCaptchaType, setFailureCaptchaType] = useState<"line" | "visual">("line");

  // ── Type-complete interstitial ──────────────────────────────────
  const [typeJustCompleted, setTypeJustCompleted] = useState<"line" | "visual" | null>(null);

  // ── Study flow: track attempts AND passes per CAPTCHA type ──────
  const [lineAttempts, setLineAttempts] = useState(0);
  const [imageAttempts, setImageAttempts] = useState(0);
  const [linePasses, setLinePasses] = useState(0);
  const [imagePasses, setImagePasses] = useState(0);

  const lineComplete = lineAttempts >= REQUIRED_ATTEMPTS;
  const imageComplete = imageAttempts >= REQUIRED_ATTEMPTS;

  // ── Consecutive failure tracking (for morale nudge) ─────────────
  const [consecutiveFailures, setConsecutiveFailures] = useState(0);

  // ── Mid-attempt reset ───────────────────────────────────────────
  const [pendingTab, setPendingTab] = useState<"line" | "visual" | null>(null);
  const lineAttemptRef = useRef<() => boolean>(() => false);
  const imageAttemptRef = useRef<() => boolean>(() => false);

  // Refs for use in timeouts
  const lineAttemptsRef = useRef(lineAttempts);
  const imageAttemptsRef = useRef(imageAttempts);
  const linePassesRef = useRef(linePasses);
  const imagePassesRef = useRef(imagePasses);
  useEffect(() => { lineAttemptsRef.current = lineAttempts; }, [lineAttempts]);
  useEffect(() => { imageAttemptsRef.current = imageAttempts; }, [imageAttempts]);
  useEffect(() => { linePassesRef.current = linePasses; }, [linePasses]);
  useEffect(() => { imagePassesRef.current = imagePasses; }, [imagePasses]);

  // ── Consent gate ──────────────────────────────────────────────
  useEffect(() => {
    const consented = sessionStorage.getItem("study_consented") === "true";
    if (!consented) {
      router.replace("/info-sheet");
      return;
    }
    const storedLineAttempts = parseInt(sessionStorage.getItem("captcha_line_attempts") || "0", 10);
    const storedImageAttempts = parseInt(sessionStorage.getItem("captcha_image_attempts") || "0", 10);
    const storedLinePasses = parseInt(sessionStorage.getItem("captcha_line_passes") || "0", 10);
    const storedImagePasses = parseInt(sessionStorage.getItem("captcha_image_passes") || "0", 10);

    if (storedLineAttempts >= REQUIRED_ATTEMPTS && storedImageAttempts >= REQUIRED_ATTEMPTS) {
      router.replace("/questionnaire");
      return;
    }
    setLineAttempts(storedLineAttempts);
    setImageAttempts(storedImageAttempts);
    setLinePasses(storedLinePasses);
    setImagePasses(storedImagePasses);
    lineAttemptsRef.current = storedLineAttempts;
    imageAttemptsRef.current = storedImageAttempts;
    linePassesRef.current = storedLinePasses;
    imagePassesRef.current = storedImagePasses;

    const startTab = storedLineAttempts >= REQUIRED_ATTEMPTS ? "visual" : "line";
    setActiveTab(startTab);
    setReady(true);
  }, [router]);

  const handleStatusChange = (newStatus: string, tone?: "info" | "error" | "success") => {
    setStatusText(newStatus);
    setStatusTone(tone || "info");
  };

  const handleTimerChange = (time: string) => {
    setTimer(time ? `Time: ${time}` : "Time: --");
  };

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
    } catch {
      setStatusText("Failed to load");
      setStatusTone("error");
    } finally {
      setIsLoading(false);
    }
  };

  const switchToTab = (tab: "line" | "visual") => {
    setActiveTab(tab);
    setConsecutiveFailures(0);
    setPendingTab(null);
    // Challenge will be loaded by TutorialOverlay.onComplete
    // (fires immediately if tutorial was already seen)
  };

  const handleTabChange = (value: string) => {
    const tab = value as "line" | "visual";
    if (tab === activeTab) return;

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

  const handleContinueFromInterstitial = () => {
    const lineDone = lineAttemptsRef.current >= REQUIRED_ATTEMPTS;
    const imageDone = imageAttemptsRef.current >= REQUIRED_ATTEMPTS;
    setTypeJustCompleted(null);

    if (lineDone && imageDone) {
      router.push("/questionnaire");
    } else {
      const nextTab = lineDone ? "visual" : "line";
      switchToTab(nextTab);
    }
  };

  const handleChallengeComplete = useCallback((success: boolean, reason?: string) => {
    const isLine = activeTab === "line";

    // ── Always increment attempt count ──────────────────────────
    const prevAttempts = isLine ? lineAttemptsRef.current : imageAttemptsRef.current;
    const newAttempts = prevAttempts + 1;

    if (isLine) {
      setLineAttempts(newAttempts);
      lineAttemptsRef.current = newAttempts;
      sessionStorage.setItem("captcha_line_attempts", String(newAttempts));
    } else {
      setImageAttempts(newAttempts);
      imageAttemptsRef.current = newAttempts;
      sessionStorage.setItem("captcha_image_attempts", String(newAttempts));
    }

    // ── Track passes ────────────────────────────────────────────
    if (success) {
      const prevPasses = isLine ? linePassesRef.current : imagePassesRef.current;
      const newPasses = prevPasses + 1;

      if (isLine) {
        setLinePasses(newPasses);
        linePassesRef.current = newPasses;
        sessionStorage.setItem("captcha_line_passes", String(newPasses));
      } else {
        setImagePasses(newPasses);
        imagePassesRef.current = newPasses;
        sessionStorage.setItem("captcha_image_passes", String(newPasses));
      }

      fireConfetti();
      setConsecutiveFailures(0);

      window.dispatchEvent(
        new CustomEvent("captcha-verified", { detail: { type: activeTab } })
      );
    } else {
      // Show failure tutorial popup — next challenge loads on dismiss
      if (reason && reason !== "error") {
        setFailureReason(reason);
        setFailureCaptchaType(activeTab);
        setFailureTutorialOpen(true);
      } else {
        // No popup (network error etc) — auto-load after delay
        if (newAttempts < REQUIRED_ATTEMPTS) {
          setTimeout(() => { loadChallenge(activeTab); }, AUTO_ADVANCE_DELAY_MS);
        }
      }
      setConsecutiveFailures((prev) => prev + 1);
    }

    // ── Check if this type just hit 5 attempts → show interstitial ──
    if (newAttempts >= REQUIRED_ATTEMPTS) {
      if (isLine) {
        sessionStorage.setItem("captcha_line_complete", "true");
      } else {
        sessionStorage.setItem("captcha_image_complete", "true");
      }
      setTimeout(() => {
        setTypeJustCompleted(isLine ? "line" : "visual");
      }, AUTO_ADVANCE_DELAY_MS);
    } else if (success) {
      // More attempts needed — auto-load next challenge (success only;
      // failures load on popup dismiss to avoid double-load)
      setTimeout(() => {
        loadChallenge(activeTab);
      }, AUTO_ADVANCE_DELAY_MS);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, router]);

  // Challenge is loaded when tutorial overlay completes (or was already seen)
  const handleTutorialComplete = useCallback(() => {
    loadChallenge(activeTab);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  // Current attempt number for display
  const currentAttempt = activeTab === "line"
    ? Math.min(lineAttempts + 1, REQUIRED_ATTEMPTS)
    : Math.min(imageAttempts + 1, REQUIRED_ATTEMPTS);

  // Nudge only for morale after 3 consecutive failures (doesn't force switch)
  const showNudge = consecutiveFailures >= CONSECUTIVE_FAILURE_NUDGE;

  if (!ready) return null;

  // ── Type-complete interstitial ──────────────────────────────────
  if (typeJustCompleted) {
    const completedLabel =
      typeJustCompleted === "line" ? "Trace the Path" : "Spot the Crossings";
    const completedPasses = typeJustCompleted === "line" ? linePasses : imagePasses;
    const bothDone =
      lineAttemptsRef.current >= REQUIRED_ATTEMPTS &&
      imageAttemptsRef.current >= REQUIRED_ATTEMPTS;
    const otherLabel =
      typeJustCompleted === "line" ? "Spot the Crossings" : "Trace the Path";

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
                {completedLabel} Complete!
              </p>
              <p className="text-2xl font-bold text-foreground">
                You scored {completedPasses}/{REQUIRED_ATTEMPTS}
              </p>
              <p className="text-sm text-muted-foreground">
                {completedPasses === REQUIRED_ATTEMPTS
                  ? "Perfect score!"
                  : completedPasses >= 3
                    ? "Great job!"
                    : "Thanks for completing all attempts."}
              </p>

              {/* Progress for both types */}
              <div className="flex flex-col gap-2 w-full max-w-[240px]">
                <div className="flex items-center justify-between gap-3">
                  <span className={`text-xs ${lineComplete ? "text-green-500 font-medium" : "text-muted-foreground"}`}>
                    Trace the Path
                  </span>
                  <AttemptDots attempts={lineAttempts} passes={linePasses} total={REQUIRED_ATTEMPTS} />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className={`text-xs ${imageComplete ? "text-green-500 font-medium" : "text-muted-foreground"}`}>
                    Spot the Crossings
                  </span>
                  <AttemptDots attempts={imageAttempts} passes={imagePasses} total={REQUIRED_ATTEMPTS} />
                </div>
              </div>

              <Button onClick={handleContinueFromInterstitial}>
                {bothDone
                  ? "Continue to Questionnaire"
                  : `Next: ${otherLabel}`}
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
            Complete both challenges — {REQUIRED_ATTEMPTS} attempts each
          </p>

          {/* Progress for both types */}
          <div className="flex flex-col gap-1.5 items-center pt-2">
            <div className="flex items-center gap-3">
              <span className={`text-xs w-28 text-right ${lineComplete ? "text-green-500 font-medium" : "text-muted-foreground"}`}>
                {lineComplete ? "\u2713 " : ""}Trace the Path
              </span>
              <AttemptDots attempts={lineAttempts} passes={linePasses} total={REQUIRED_ATTEMPTS} />
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs w-28 text-right ${imageComplete ? "text-green-500 font-medium" : "text-muted-foreground"}`}>
                {imageComplete ? "\u2713 " : ""}Spot the Crossings
              </span>
              <AttemptDots attempts={imageAttempts} passes={imagePasses} total={REQUIRED_ATTEMPTS} />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <TutorialOverlay type={activeTab} onComplete={handleTutorialComplete} />
          <Tabs
            value={activeTab}
            className="w-full"
            onValueChange={handleTabChange}
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="line" disabled={lineComplete}>
                {lineComplete ? "\u2713 " : ""}Trace the Path
              </TabsTrigger>
              <TabsTrigger value="visual" disabled={imageComplete}>
                {imageComplete ? "\u2713 " : ""}Spot the Crossings
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Attempt counter */}
          <p className="mt-3 text-center text-sm font-medium text-muted-foreground">
            Attempt {currentAttempt} of {REQUIRED_ATTEMPTS}
          </p>

          {/* Mid-attempt switch warning */}
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

            <div className="flex w-full items-center justify-end gap-4 border-t border-border pt-4">
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

            {/* Morale nudge after 3 consecutive failures */}
            {showNudge && (
              <p className="text-sm text-muted-foreground text-center">
                Keep going — you&apos;re doing great! Each attempt helps the research.
              </p>
            )}
          </div>
        </CardContent>
      </Card>
      <FeedbackWidget />
      <FailureTutorial
        open={failureTutorialOpen}
        onDismiss={() => {
          setFailureTutorialOpen(false);
          // Auto-load next challenge after failure popup is dismissed
          const la = lineAttemptsRef.current;
          const ia = imageAttemptsRef.current;
          const currentDone = activeTab === "line" ? la >= REQUIRED_ATTEMPTS : ia >= REQUIRED_ATTEMPTS;
          if (!currentDone) {
            loadChallenge(activeTab);
          }
        }}
        captchaType={failureCaptchaType}
        failureReason={failureReason}
      />
    </main>
  );
}
