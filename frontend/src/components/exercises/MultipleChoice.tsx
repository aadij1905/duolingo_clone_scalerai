"use client";
import { useEffect, useState } from "react";
import { speak } from "@/lib/sound";
import type { ExerciseProps } from "./types";
import s from "../lesson.module.css";

/** Picture cards (or big letters, for the alphabet skill); keys 1-3 select like on Duolingo.
 *  Selecting plays the option, or its example word (`say`); `say: null` stays silent. */
export default function MultipleChoice({ exercise, onChange, locked }: ExerciseProps<"multiple_choice">) {
  const [picked, setPicked] = useState<number | null>(null);
  const options = exercise.payload.options;

  const pick = (i: number) => {
    if (locked) return;
    setPicked(i);
    onChange(options[i].text);
    const say = options[i].say === undefined ? options[i].text : options[i].say;
    if (say) speak(say);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const n = Number(e.key);
      if (n >= 1 && n <= options.length && !locked) pick(n - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <>
    {exercise.payload.new_word && <span className={s.badge}>✨ New word</span>}
    <div className={s.choices} role="radiogroup">
      {options.map((o, i) => (
        <button key={o.text} role="radio" aria-checked={picked === i} className={`${s.choice} ${picked === i ? s.selected : ""}`} onClick={() => pick(i)}>
          {o.emoji ? <>
            <span className={s.emoji} aria-hidden>{o.emoji}</span>
            <span className={s.text}>
              <span>{o.text}{o.reading && <small className={s.reading}>{o.reading}</small>}</span>
              <span className={s.key}>{i + 1}</span>
            </span>
          </> : <>
            <span className={`${s.emoji} ${o.text.length > 3 ? s.soundText : ""}`}>{o.text}</span>
            <span className={s.text}><span /><span className={s.key}>{i + 1}</span></span>
          </>}
        </button>
      ))}
    </div>
    </>
  );
}
