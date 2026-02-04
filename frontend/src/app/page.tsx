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
import { Challenge, fetchChallenge } from "@/lib/api";

const CAPTCHA_INSTRUCTIONS = {
  line: "Press/touch the blue start point and follow the line as it appears. Do not lift until done.",
  visual: "Click the single unique abstract puzzle piece.",
};

export default function CaptchaPage() {
  const [instruction, setInstruction] = useState(CAPTCHA_INSTRUCTIONS.line);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
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
    // Could add analytics or other completion handling here
    console.log("Challenge completed:", success ? "passed" : "failed");
  };

  const handleNewChallenge = async () => {
    setIsLoading(true);
    setStatusText("");
    setStatusTone("info");
    setTimer("Time: --");

    try {
      const newChallenge = await fetchChallenge();
      setChallenge(newChallenge);
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

  const handleTabChange = (value: string) => {
    if (value === "line" || value === "visual") {
      setInstruction(CAPTCHA_INSTRUCTIONS[value as keyof typeof CAPTCHA_INSTRUCTIONS]);
      if (value === "line") {
        handleNewChallenge();
      }
    }
  };

  // Load initial challenge
  useEffect(() => {
    handleNewChallenge();
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
              <TabsTrigger value="visual" disabled>Visual CAPTCHA</TabsTrigger>
            </TabsList>
          </Tabs>

          <div className="mt-4 sm:mt-6 flex flex-col items-center gap-4">
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
