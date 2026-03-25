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

const FALLBACK_AFTER_FAILURES = 3;
const REQUIRED_PASSES = 3;
const AUTO_ADVANCE_DELAY_MS = 1800;

function PassDots({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1.5">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-2.5 w-2.5 rounded-full transition-all duration-500 ${
            i < current ? "bg-green-500 scale-110" : "bg-muted-foreground/25"
          }`}
        />
      ))}
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

  // ── Type-complete interstitial (shown when a type hits 3/3) ─────
  const [typeJustCompleted, setTypeJustCompleted] = useState<"line" | "visual" | null>(null);

  // ── Study flow: track pass counts per CAPTCHA type ──────────────
  const [linePasses, setLinePasses] = useState(0);
  const [imagePasses, setImagePasses] = useState(0);

  const lineComplete = linePasses >= REQUIRED_PASSES;
  const imageComplete = imagePasses >= REQUIRED_PASSES;

  // ── Failure tracking (5.4) ────────────────────────────────────
  const [lineFailures, setLineFailures] = useState(0);
  const [imageFailures, setImageFailures] = useState(0);

  // ── Mid-attempt reset (5.2) ───────────────────────────────────
  const [pendingTab, setPendingTab] = useState<"line" | "visual" | null>(null);
  const lineAttemptRef = useRef<() => boolean>(() => false);
  const imageAttemptRef = useRef<() => boolean>(() => false);

  // Ref to track latest pass counts for use in timeouts
  const linePassesRef = useRef(linePasses);
  const imagePassesRef = useRef(imagePasses);
  useEffect(() => { linePassesRef.current = linePasses; }, [linePasses]);
  useEffect(() => { imagePassesRef.current = imagePasses; }, [imagePasses]);

  // ── Consent gate ──────────────────────────────────────────────
  useEffect(() => {
    const consented = sessionStorage.getItem("study_consented") === "true";
    if (!consented) {
      router.replace("/info-sheet");
      return;
    }
    const storedLine = parseInt(sessionStorage.getItem("captcha_line_passes") || "0", 10);
    const storedImage = parseInt(sessionStorage.getItem("captcha_image_passes") || "0", 10);
    if (storedLine >= REQUIRED_PASSES && storedImage >= REQUIRED_PASSES) {
      router.replace("/questionnaire");
      return;
    }
    setLinePasses(storedLine);
    setImagePasses(storedImage);
    linePassesRef.current = storedLine;
    imagePassesRef.current = storedImage;
    const startTab = storedLine >= REQUIRED_PASSES ? "visual" : "line";
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

  const handleNewChallenge = () => loadChallenge(activeTab);

  const switchToTab = (tab: "line" | "visual") => {
    setActiveTab(tab);
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
    const lineDone = linePassesRef.current >= REQUIRED_PASSES;
    const imageDone = imagePassesRef.current >= REQUIRED_PASSES;
    setTypeJustCompleted(null);

    if (lineDone && imageDone) {
      router.push("/questionnaire");
    } else {
      const nextTab = lineDone ? "visual" : "line";
      switchToTab(nextTab);
    }
  };

  const handleChallengeComplete = useCallback((success: boolean, reason?: string) => {
    if (success) {
      const isLine = activeTab === "line";
      const prevPasses = isLine ? linePassesRef.current : imagePassesRef.current;
      const newCount = Math.min(prevPasses + 1, REQUIRED_PASSES);

      if (isLine) {
        setLinePasses(newCount);
        linePassesRef.current = newCount;
        sessionStorage.setItem("captcha_line_passes", String(newCount));
        if (newCount >= REQUIRED_PASSES) {
          sessionStorage.setItem("captcha_line_complete", "true");
        }
      } else {
        setImagePasses(newCount);
        imagePassesRef.current = newCount;
        sessionStorage.setItem("captcha_image_passes", String(newCount));
        if (newCount >= REQUIRED_PASSES) {
          sessionStorage.setItem("captcha_image_complete", "true");
        }
      }

      // Fire confetti
      fireConfetti();

      window.dispatchEvent(
        new CustomEvent("captcha-verified", { detail: { type: activeTab } })
      );
      setLineFailures(0);
      setImageFailures(0);

      // Check if this type just hit 3/3 — show interstitial
      const justCompleted = newCount >= REQUIRED_PASSES;
      if (justCompleted) {
        setTimeout(() => {
          setTypeJustCompleted(isLine ? "line" : "visual");
        }, AUTO_ADVANCE_DELAY_MS);
      } else {
        // Still more passes needed — auto-load next challenge
        setTimeout(() => {
          loadChallenge(activeTab);
        }, AUTO_ADVANCE_DELAY_MS);
      }
    } else {
      // Show failure tutorial popup
      if (reason && reason !== "error") {
        setFailureReason(reason);
        setFailureCaptchaType(activeTab);
        setFailureTutorialOpen(true);
      }

      if (activeTab === "line") {
        setLineFailures((prev) => prev + 1);
      } else {
        setImageFailures((prev) => prev + 1);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, router]);

  // Load initial challenge once ready
  useEffect(() => {
    if (ready) {
      loadChallenge(activeTab);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready]);

  // Derive nudge messages
  const showLineNudge = lineFailures >= FALLBACK_AFTER_FAILURES;
  const showImageNudge = imageFailures >= FALLBACK_AFTER_FAILURES;
  const showNudge =
    (activeTab === "line" && showLineNudge) ||
    (activeTab === "visual" && showImageNudge);
  const nudgeTarget = activeTab === "line" ? "visual" : "line";
  const nudgeLabel =
    nudgeTarget === "line" ? "Trace the Path" : "Spot the Crossings";

  if (!ready) return null;

  // ── Type-complete interstitial ──────────────────────────────────
  if (typeJustCompleted) {
    const completedLabel =
      typeJustCompleted === "line" ? "Trace the Path" : "Spot the Crossings";
    const bothDone = linePassesRef.current >= REQUIRED_PASSES && imagePassesRef.current >= REQUIRED_PASSES;
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
              <p className="text-sm text-muted-foreground">
                You passed all {REQUIRED_PASSES} attempts.
              </p>

              {/* Progress for both types */}
              <div className="flex flex-col gap-2 w-full max-w-[220px]">
                <div className="flex items-center justify-between gap-3">
                  <span className={`text-xs ${lineComplete ? "text-green-500 font-medium" : "text-muted-foreground"}`}>
                    Trace the Path
                  </span>
                  <PassDots current={linePasses} total={REQUIRED_PASSES} />
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className={`text-xs ${imageComplete ? "text-green-500 font-medium" : "text-muted-foreground"}`}>
                    Spot the Crossings
                  </span>
                  <PassDots current={imagePasses} total={REQUIRED_PASSES} />
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
            Verify you&apos;re human — complete both challenges
          </p>

          {/* Progress for both types */}
          <div className="flex flex-col gap-1.5 items-center pt-2">
            <div className="flex items-center gap-3">
              <span className={`text-xs w-28 text-right ${lineComplete ? "text-green-500 font-medium" : "text-muted-foreground"}`}>
                {lineComplete ? "\u2713 " : ""}Trace the Path
              </span>
              <PassDots current={linePasses} total={REQUIRED_PASSES} />
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-xs w-28 text-right ${imageComplete ? "text-green-500 font-medium" : "text-muted-foreground"}`}>
                {imageComplete ? "\u2713 " : ""}Spot the Crossings
              </span>
              <PassDots current={imagePasses} total={REQUIRED_PASSES} />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <TutorialOverlay type={activeTab} />
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
      <FailureTutorial
        open={failureTutorialOpen}
        onDismiss={() => setFailureTutorialOpen(false)}
        captchaType={failureCaptchaType}
        failureReason={failureReason}
      />
    </main>
  );
}
