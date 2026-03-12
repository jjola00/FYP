"use client";

import { useRouter } from "next/navigation";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";

const CONSENT_STATEMENTS = [
  "I declare that I have been fully briefed on the nature of this study and my role in it and have been given the opportunity to ask questions before agreeing to participate.",
  "The nature of my participation has been explained to me, and I have full knowledge of how the information collected will be used.",
  "I am aware that such information may also be used in future academic presentations and publications about this study.",
  "I fully understand that there is no obligation on me to participate in this study.",
  "I fully understand that I am free to withdraw my participation without having to explain or give a reason, up to a period of two weeks after the data collection is completed.",
  "I acknowledge that the researcher guarantees that they will not use my name or any other information that would identify me in any outputs of the research.",
  "I declare that I am over 18 years of age.",
  "I declare that I have read and fully understand the contents of the Research Privacy Notice.",
];

export default function ConsentPage() {
  const router = useRouter();
  const [checked, setChecked] = useState<boolean[]>(
    new Array(CONSENT_STATEMENTS.length).fill(false)
  );
  const [declined, setDeclined] = useState(false);

  useEffect(() => {
    // If already consented, skip ahead
    if (sessionStorage.getItem("study_consented") === "true") {
      router.replace("/");
      return;
    }
  }, [router]);

  const allChecked = checked.every(Boolean);

  const toggleCheck = (index: number) => {
    setChecked((prev) => {
      const next = [...prev];
      next[index] = !next[index];
      return next;
    });
  };

  const handleCheckAll = () => {
    setChecked(new Array(CONSENT_STATEMENTS.length).fill(true));
  };

  const handleAgree = () => {
    sessionStorage.setItem("study_consented", "true");
    sessionStorage.setItem("study_step", "captcha");
    // Reset tutorial flags so tutorials show for this study session
    localStorage.removeItem("tutorial_seen_line");
    localStorage.removeItem("tutorial_seen_image");
    router.push("/");
  };

  if (declined) {
    return (
      <main className="flex min-h-dvh flex-col items-center justify-center p-2 sm:p-4">
        <Card className="w-full max-w-sm sm:max-w-md shadow-2xl shadow-primary/10">
          <CardHeader>
            <CardTitle className="font-headline text-center text-lg font-bold text-primary sm:text-xl md:text-2xl">
              Beyond Recognition
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4 py-8">
            <p className="text-center text-foreground">
              Thank you for your time. You have chosen not to participate in this
              study.
            </p>
            <p className="text-center text-sm text-muted-foreground">
              You may close this window.
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center p-2 sm:p-4">
      <Card className="w-full max-w-sm sm:max-w-2xl shadow-2xl shadow-primary/10">
        <CardHeader className="relative">
          <div className="absolute top-4 right-4 sm:top-6 sm:right-6">
            <ThemeToggle />
          </div>
          <CardTitle className="font-headline text-center text-lg font-bold text-primary sm:text-xl md:text-2xl">
            Ethical Consent Form
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-relaxed text-foreground">
          <p className="italic">
            I, the undersigned, declare that I am willing to take part in
            research for the project entitled: &ldquo;Beyond Recognition&rdquo;.
          </p>

          <div className="space-y-3">
            {CONSENT_STATEMENTS.map((statement, i) => (
              <label
                key={i}
                className="flex items-start gap-3 cursor-pointer rounded-md border border-border p-3 transition-colors hover:bg-muted/50"
              >
                <input
                  type="checkbox"
                  checked={checked[i]}
                  onChange={() => toggleCheck(i)}
                  className="mt-0.5 h-4 w-4 shrink-0 rounded border-border accent-primary"
                />
                <span>{statement}</span>
              </label>
            ))}
          </div>

          <div className="flex flex-col items-center gap-3 pt-4">
            {!allChecked && (
              <button
                className="text-sm text-muted-foreground underline hover:text-foreground transition-colors"
                onClick={handleCheckAll}
              >
                Check all
              </button>
            )}
            <Button
              size="lg"
              disabled={!allChecked}
              onClick={handleAgree}
            >
              I Agree &amp; Continue
            </Button>
            <button
              className="text-sm text-muted-foreground underline hover:text-foreground transition-colors"
              onClick={() => setDeclined(true)}
            >
              I do not wish to participate
            </button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
