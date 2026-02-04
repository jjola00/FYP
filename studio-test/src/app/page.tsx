"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ThemeToggle } from "@/components/theme-toggle";

const CAPTCHA_INSTRUCTIONS = {
  line: "Trace the curved path shown on the canvas with your mouse.",
  visual: "Click the single unique abstract puzzle piece.",
};

export default function CaptchaPage() {
  const [instruction, setInstruction] = useState(CAPTCHA_INSTRUCTIONS.line);

  const handleTabChange = (value: string) => {
    if (value === "line" || value === "visual") {
      setInstruction(CAPTCHA_INSTRUCTIONS[value as keyof typeof CAPTCHA_INSTRUCTIONS]);
    }
  };

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
            <div className="relative w-full max-w-[300px] sm:max-w-[350px] aspect-square">
              <canvas
                id="captcha-canvas"
                width="350"
                height="350"
                className="rounded-lg border-2 border-accent bg-muted/50 w-full h-full"
                aria-label="CAPTCHA challenge area"
              />
            </div>

            <p className="flex min-h-[3rem] items-center text-center text-sm text-muted-foreground sm:min-h-[2.5rem]">
              {instruction}
            </p>

            <div className="flex w-full items-center justify-between gap-4 border-t border-border pt-4">
              <Button id="reload-btn" variant="outline">
                New Challenge
              </Button>
              <div className="flex flex-col items-end">
                <p
                  id="status"
                  className="text-sm text-muted-foreground"
                  aria-live="polite"
                >
                  Status: Ready
                </p>
                <p id="timer" className="font-mono text-sm text-primary">
                  Time: --
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
