import confetti from "canvas-confetti";
import { useCallback } from "react";

export function useConfetti() {
  const fireConfetti = useCallback(() => {
    confetti({
      particleCount: 70,
      spread: 70,
      startVelocity: 45,
      origin: { y: 0.6 },
    });

    setTimeout(() => {
      confetti({
        particleCount: 50,
        spread: 90,
        startVelocity: 35,
        origin: { y: 0.65 },
      });
    }, 160);

    setTimeout(() => {
      confetti({
        particleCount: 90,
        spread: 110,
        startVelocity: 55,
        origin: { y: 0.55 },
      });
    }, 320);
  }, []);

  return { fireConfetti };
}
