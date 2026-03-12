"use client";

import { useEffect } from "react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";

export default function ThankYouPage() {
  useEffect(() => {
    // Clear study session data
    sessionStorage.setItem("study_step", "complete");
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
            <h2 className="text-lg font-semibold text-foreground">
              Thank You!
            </h2>
            <div className="space-y-3 text-center text-sm text-muted-foreground max-w-md">
              <p>
                Your participation in this study is greatly appreciated. Your
                responses have been recorded anonymously and will contribute to
                research on improving CAPTCHA usability and security.
              </p>
              <p>
                If you have any questions or concerns about this study, please
                contact Oluwajomiloju Olajitan at{" "}
                <span className="text-foreground">23373326@studentmail.ul.ie</span>{" "}
                or Dr Roisin Lyons at{" "}
                <span className="text-foreground">Roisin.Lyons@ul.ie</span>.
              </p>
              <p>You may now close this window.</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
