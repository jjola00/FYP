"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ThemeToggle } from "@/components/theme-toggle";

export default function InfoSheetPage() {
  const router = useRouter();

  useEffect(() => {
    // If already consented, skip ahead to captcha
    if (sessionStorage.getItem("study_consented") === "true") {
      router.replace("/");
      return;
    }
    // Mark that the study has started
    sessionStorage.setItem("study_step", "info");
  }, [router]);

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center p-2 sm:p-4">
      <Card className="w-full max-w-sm sm:max-w-2xl shadow-2xl shadow-primary/10">
        <CardHeader className="relative">
          <div className="absolute top-4 right-4 sm:top-6 sm:right-6">
            <ThemeToggle />
          </div>
          <CardTitle className="font-headline text-center text-lg font-bold text-primary sm:text-xl md:text-2xl">
            Beyond Recognition
          </CardTitle>
          <p className="text-center text-sm text-muted-foreground">
            Participant Information Sheet
          </p>
        </CardHeader>
        <CardContent className="space-y-4 text-sm leading-relaxed text-foreground">
          <p>Dear Participant,</p>

          <p>
            My name is Oluwajomiloju Olajitan and I am currently undertaking a
            Final Year Project at the University of Limerick under the
            supervision of Dr. Roisin Lyons. The title of my proposed research
            is{" "}
            <em>
              Beyond Recognition: Reframing CAPTCHAs as Human-Usable Moving
              Target Defences
            </em>
            . The purpose of this project is to investigate if I can improve the
            security of CAPTCHAs while retaining human usability.
          </p>

          <p>
            As part of this study, you will be asked to complete 2 CAPTCHA
            challenges. These tasks will take place online in your web browser
            and will involve, for example, tracing a simple path with your mouse
            or finger and clicking on shapes or images to solve small puzzles.
            The session will take approximately 5&ndash;10 minutes in total.
          </p>

          <p>
            There are no anticipated risks beyond potential temporary frustration
            similar to using ordinary CAPTCHAs on websites. You may take breaks
            and you are free to stop participating at any time without giving a
            reason and without any negative consequences. No video or audio
            recording will take place and your data will be anonymised.
          </p>

          <p>
            Your participation is voluntary, and you have the right to withdraw
            at any time. To participate in this study, you must be over 18 years
            of age.
          </p>

          <p>
            If you have further questions regarding this research, please feel
            free to get in touch with either myself or my supervisor using the
            email addresses listed below.
          </p>

          <p>
            If you have concerns about this study and wish to contact someone
            independent, you may contact: The Chair, Faculty of Science &amp;
            Engineering Research Ethics Committee, University of Limerick,
            Limerick. Tel: 061 213324
          </p>

          <p>Yours sincerely,</p>

          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr>
                  <th className="border border-border px-3 py-2 text-left font-semibold">
                    Oluwajomiloju Olajitan
                  </th>
                  <th className="border border-border px-3 py-2 text-left font-semibold">
                    Dr Roisin Lyons
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="border border-border px-3 py-2">
                    23373326@studentmail.ul.ie
                  </td>
                  <td className="border border-border px-3 py-2">
                    Dept. of Management &amp; Marketing
                  </td>
                </tr>
                <tr>
                  <td className="border border-border px-3 py-2"></td>
                  <td className="border border-border px-3 py-2">
                    003531 7006474
                  </td>
                </tr>
                <tr>
                  <td className="border border-border px-3 py-2"></td>
                  <td className="border border-border px-3 py-2">
                    Roisin.Lyons@ul.ie
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="flex justify-center pt-4">
            <Button
              size="lg"
              onClick={() => router.push("/consent")}
            >
              Continue
            </Button>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
