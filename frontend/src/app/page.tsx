"use client";

import { useState, useEffect } from "react";
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
import {
  Challenge,
  ImageChallenge,
  fetchChallenge,
  fetchImageChallenge,
} from "@/lib/api";

const LINE_INSTRUCTION =
  "Press/touch the blue start point and follow the line as it appears. Do not lift until done.";

export default function CaptchaPage() {
  const [activeTab, setActiveTab] = useState<"line" | "visual">("line");
  const [instruction, setInstruction] = useState(LINE_INSTRUCTION);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [imageChallenge, setImageChallenge] = useState<ImageChallenge | null>(null);
  const [statusText, setStatusText] = useState("");
  const [statusTone, setStatusTone] = useState<"info" | "error" | "success">("info");
  const [timer, setTimer] = useState("Time: --");
  const [isLoading, setIsLoading] = useState(false);

  const handleStatusChange = (newStatus: string, tone?: "info" | "error" | "success") => {
    setStatusText(newStatus);
    setStatusTone(tone || "info");
  };

  const handleTimerChange = (time: string) => {
    setTimer(time ? `Time: ${time}` : "Time: --");
  };

  const handleChallengeComplete = (success: boolean) => {
    console.log("Challenge completed:", success ? "passed" : "failed");
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
    } catch (error) {
      console.error("Failed to fetch challenge:", error);
      setStatusText("Failed to load");
      setStatusTone("error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChallenge = () => loadChallenge(activeTab);

  const handleTabChange = (value: string) => {
    const tab = value as "line" | "visual";
    setActiveTab(tab);
    loadChallenge(tab);
  };

  // Load initial challenge
  useEffect(() => {
    loadChallenge("line");
  }, []);

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
          <Tabs
            defaultValue="line"
            className="w-full"
            onValueChange={handleTabChange}
          >
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="line">Line CAPTCHA</TabsTrigger>
              <TabsTrigger value="visual">Visual CAPTCHA</TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="mt-4 sm:mt-6 flex flex-col items-center gap-4">
            {activeTab === "line" ? (
              <div className="relative w-full max-w-[350px] aspect-square">
                {challenge ? (
                  <CaptchaCanvas
                    challenge={challenge}
                    onStatusChange={handleStatusChange}
                    onTimerChange={handleTimerChange}
                    onChallengeComplete={handleChallengeComplete}
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
                  aria-live="polite"
                >
                  {statusText || "Status"}
                </p>
                <p className="font-mono text-sm text-primary">
                  {timer}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
