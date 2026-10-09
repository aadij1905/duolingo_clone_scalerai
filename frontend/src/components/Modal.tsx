"use client";
import { useEffect } from "react";

/** Accessible modal: dialog role, Escape to close, click outside to close. */
export default function Modal({ children, onClose, label }: { children: React.ReactNode; onClose?: () => void; label: string }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={label} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  );
}

/** Celebration confetti: pure CSS animation, no library. */
export function Confetti({ pieces = 80 }: { pieces?: number }) {
  const colors = ["#58cc02", "#1cb0f6", "#ff4b4b", "#ffc800", "#ce82ff", "#ff9600"];
  return (
    <div aria-hidden style={{ position: "fixed", inset: 0, pointerEvents: "none", overflow: "hidden", zIndex: 150 }}>
      {Array.from({ length: pieces }, (_, i) => (
        <span key={i} style={{
          position: "absolute", top: -20, left: `${(i * 37) % 100}%`,
          width: 8 + (i % 3) * 3, height: 12 + (i % 4) * 2, borderRadius: i % 2 ? 2 : 99,
          background: colors[i % colors.length],
          animation: `confetti-fall ${2.2 + (i % 5) * 0.35}s ${(i % 10) * 0.08}s cubic-bezier(.3,.6,.6,1) forwards`,
        }} />
      ))}
    </div>
  );
}
