"use client";
import { useState } from "react";
import { speak } from "@/lib/sound";
import { HintText } from "./parts";
import type { ExerciseProps } from "./types";
import s from "../lesson.module.css";

/** Sentence with a gap; pick the word that completes it. */
export default function FillBlank({ exercise, onChange, locked }: ExerciseProps<"fill_blank">) {
  const { before, after, options, translation } = exercise.payload;
  const [picked, setPicked] = useState<string | null>(null);
  const pick = (w: string) => {
    if (locked) return;
    const next = picked === w ? null : w;
    setPicked(next);
    onChange(next);
    if (next) speak(next);
  };
  return (
    <>
      <p className={s.hint}>“{translation}”</p>
      <div className={s.sentence}>
        {before.length > 0 && <HintText tokens={before} />}
        <span className={s.blank}>{picked ?? " "}</span>
        {after.length > 0 && <HintText tokens={after} />}
      </div>
      <div className={s.options}>
        {options.map((o) => (
          <button key={o} className={`${s.tile} ${picked === o ? s.selected : ""}`} onClick={() => pick(o)}>{o}</button>
        ))}
      </div>
    </>
  );
}
