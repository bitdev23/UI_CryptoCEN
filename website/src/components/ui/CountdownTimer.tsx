"use client";

import { useState, useEffect } from "react";

export function CountdownTimer() {
  const [timeLeft, setTimeLeft] = useState<{ hours: number; minutes: number; seconds: number } | null>(null);

  useEffect(() => {
    // Initial time: 2 hours, 14 minutes, 33 seconds (arbitrary for realism)
    const initialSeconds = 2 * 3600 + 14 * 60 + 33;
    
    // Check if there's a stored end time in session storage
    const storedEndTime = sessionStorage.getItem("velank_offer_end");
    let endTime: number;

    if (storedEndTime) {
      endTime = parseInt(storedEndTime, 10);
    } else {
      endTime = Date.now() + initialSeconds * 1000;
      sessionStorage.setItem("velank_offer_end", endTime.toString());
    }

    const timer = setInterval(() => {
      const now = Date.now();
      const distance = endTime - now;

      if (distance < 0) {
        // Reset the timer for infinite urgency if it hits zero
        const newEndTime = Date.now() + initialSeconds * 1000;
        sessionStorage.setItem("velank_offer_end", newEndTime.toString());
        return;
      }

      const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);

      setTimeLeft({ hours, minutes, seconds });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  if (!timeLeft) return null;

  const format = (num: number) => num.toString().padStart(2, "0");

  return (
    <div className="flex items-center gap-1 font-mono tabular-nums text-white bg-white/20 px-2 py-0.5 rounded border border-white/20 group-hover:bg-white/30 transition-colors">
      <span className="text-[9px] opacity-70 uppercase mr-1">OFFER ENDS:</span>
      <span className="text-indigo-100">{format(timeLeft.hours)}</span>
      <span className="opacity-50">:</span>
      <span className="text-indigo-100">{format(timeLeft.minutes)}</span>
      <span className="opacity-50">:</span>
      <span className="text-indigo-100">{format(timeLeft.seconds)}</span>
    </div>
  );
}
