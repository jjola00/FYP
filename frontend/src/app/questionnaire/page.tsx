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
import { getSessionId, submitQuestionnaire } from "@/lib/api";

const AGE_RANGES = ["18–24", "25–34", "35–44", "45–54", "55+"];

function LikertScale({
  name,
  value,
  onChange,
  lowLabel,
  highLabel,
}: {
  name: string;
  value: number | null;
  onChange: (v: number) => void;
  lowLabel: string;
  highLabel: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>{lowLabel}</span>
        <span>{highLabel}</span>
      </div>
      <div className="flex items-center justify-between gap-2">
        {[1, 2, 3, 4, 5].map((n) => (
          <label key={n} className="flex flex-col items-center gap-1 cursor-pointer">
            <input
              type="radio"
              name={name}
              value={n}
              checked={value === n}
              onChange={() => onChange(n)}
              className="h-4 w-4 accent-primary"
            />
            <span className="text-xs font-medium">{n}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

export default function QuestionnairePage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Form state
  const [deviceType, setDeviceType] = useState<string | null>(null);
  const [ageRange, setAgeRange] = useState<string | null>(null);
  const [captchaFrequency, setCaptchaFrequency] = useState<number | null>(null);
  const [captcha1Difficulty, setCaptcha1Difficulty] = useState<number | null>(null);
  const [captcha1Frustration, setCaptcha1Frustration] = useState<number | null>(null);
  const [captcha2Difficulty, setCaptcha2Difficulty] = useState<number | null>(null);
  const [captcha2Frustration, setCaptcha2Frustration] = useState<number | null>(null);
  const [comments, setComments] = useState("");

  useEffect(() => {
    // Gate: must have completed 5 attempts of each CAPTCHA type
    const lineAttempts = parseInt(sessionStorage.getItem("captcha_line_attempts") || "0", 10);
    const imageAttempts = parseInt(sessionStorage.getItem("captcha_image_attempts") || "0", 10);
    if (lineAttempts < 5 || imageAttempts < 5) {
      router.replace("/");
      return;
    }
  }, [router]);

  const isValid =
    deviceType !== null &&
    ageRange !== null &&
    captchaFrequency !== null &&
    captcha1Difficulty !== null &&
    captcha1Frustration !== null &&
    captcha2Difficulty !== null &&
    captcha2Frustration !== null;

  const handleSubmit = async () => {
    if (!isValid) return;
    setSubmitting(true);
    setError("");

    try {
      await submitQuestionnaire({
        sessionId: getSessionId(),
        deviceType: deviceType!,
        ageRange: ageRange!,
        captchaFrequency: captchaFrequency!,
        captcha1Difficulty: captcha1Difficulty!,
        captcha1Frustration: captcha1Frustration!,
        captcha2Difficulty: captcha2Difficulty!,
        captcha2Frustration: captcha2Frustration!,
        comments: comments || undefined,
      });
      sessionStorage.setItem("study_step", "complete");
      router.push("/thank-you");
    } catch {
      setError("Failed to submit. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center p-2 sm:p-4">
      <Card className="w-full max-w-sm sm:max-w-2xl shadow-2xl shadow-primary/10">
        <CardHeader className="relative">
          <div className="absolute top-4 right-4 sm:top-6 sm:right-6">
            <ThemeToggle />
          </div>
          <CardTitle className="font-headline text-center text-lg font-bold text-primary sm:text-xl md:text-2xl">
            Post-Task Questionnaire
          </CardTitle>
          <p className="text-center text-sm text-muted-foreground">
            Please answer the following questions about your experience.
          </p>
        </CardHeader>
        <CardContent className="space-y-6 text-sm">
          {/* Section 1: Demographics */}
          <div className="space-y-4">
            <h3 className="font-semibold text-foreground">Section 1: Demographics</h3>

            <div className="space-y-2">
              <p className="font-medium text-foreground">
                1. What device are you using right now?
              </p>
              <div className="flex flex-wrap gap-2">
                {["Computer", "Phone", "Tablet"].map((device) => (
                  <label
                    key={device}
                    className="flex items-center gap-2 cursor-pointer rounded-md border border-border px-3 py-2 transition-colors hover:bg-muted/50"
                  >
                    <input
                      type="radio"
                      name="deviceType"
                      value={device}
                      checked={deviceType === device}
                      onChange={() => setDeviceType(device)}
                      className="h-4 w-4 accent-primary"
                    />
                    <span>{device}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <p className="font-medium text-foreground">
                2. What is your age range?
              </p>
              <div className="flex flex-wrap gap-2">
                {AGE_RANGES.map((range) => (
                  <label
                    key={range}
                    className="flex items-center gap-2 cursor-pointer rounded-md border border-border px-3 py-2 transition-colors hover:bg-muted/50"
                  >
                    <input
                      type="radio"
                      name="ageRange"
                      value={range}
                      checked={ageRange === range}
                      onChange={() => setAgeRange(range)}
                      className="h-4 w-4 accent-primary"
                    />
                    <span>{range}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <p className="font-medium text-foreground">
                3. How often do you encounter CAPTCHAs online?
              </p>
              <LikertScale
                name="captchaFrequency"
                value={captchaFrequency}
                onChange={setCaptchaFrequency}
                lowLabel="1 = Rarely"
                highLabel="5 = Very often"
              />
            </div>
          </div>

          {/* Section 2: CAPTCHA Feedback */}
          <div className="space-y-4">
            <h3 className="font-semibold text-foreground">
              Section 2: CAPTCHA Feedback
            </h3>

            <div className="space-y-2">
              <p className="font-medium text-foreground">
                4. How difficult was CAPTCHA 1 (Trace the Path)?
              </p>
              <LikertScale
                name="captcha1Difficulty"
                value={captcha1Difficulty}
                onChange={setCaptcha1Difficulty}
                lowLabel="1 = Easiest"
                highLabel="5 = Hardest"
              />
            </div>

            <div className="space-y-2">
              <p className="font-medium text-foreground">
                5. How frustrating was CAPTCHA 1 (Trace the Path)?
              </p>
              <LikertScale
                name="captcha1Frustration"
                value={captcha1Frustration}
                onChange={setCaptcha1Frustration}
                lowLabel="1 = Least frustrating"
                highLabel="5 = Most frustrating"
              />
            </div>

            <div className="space-y-2">
              <p className="font-medium text-foreground">
                6. How difficult was CAPTCHA 2 (Spot the Crossings)?
              </p>
              <LikertScale
                name="captcha2Difficulty"
                value={captcha2Difficulty}
                onChange={setCaptcha2Difficulty}
                lowLabel="1 = Easiest"
                highLabel="5 = Hardest"
              />
            </div>

            <div className="space-y-2">
              <p className="font-medium text-foreground">
                7. How frustrating was CAPTCHA 2 (Spot the Crossings)?
              </p>
              <LikertScale
                name="captcha2Frustration"
                value={captcha2Frustration}
                onChange={setCaptcha2Frustration}
                lowLabel="1 = Least frustrating"
                highLabel="5 = Most frustrating"
              />
            </div>

            <div className="space-y-2">
              <p className="font-medium text-foreground">
                8. Any additional comments? (optional)
              </p>
              <textarea
                value={comments}
                onChange={(e) => setComments(e.target.value)}
                placeholder="Share any thoughts about your experience..."
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring min-h-[80px] resize-y"
                maxLength={2000}
              />
            </div>
          </div>

          {error && (
            <p className="text-sm text-red-500 text-center">{error}</p>
          )}

          <div className="flex justify-center pt-2">
            <Button
              size="lg"
              disabled={!isValid || submitting}
              onClick={handleSubmit}
            >
              {submitting ? "Submitting..." : "Submit"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
