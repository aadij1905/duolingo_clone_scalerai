"use client";
import { useMemo, useRef, useState } from "react";
import { sfx, speak } from "@/lib/sound";
import type { ExerciseProps } from "./types";
import s from "../lesson.module.css";

function shuffled<T>(items: T[], seed: number): T[] {
  // Deterministic shuffle so React re-renders don't reorder the columns.
  return items.map((v, i) => ({ v, k: Math.sin(seed * 9301 + i * 49297) })).sort((a, b) => a.k - b.k).map((x) => x.v);
}

/** Tap a target-language word then its English match. Mismatches flash red; when every
 *  pair is found the full set is reported as the answer (auto-checked). */
export default function MatchPairs({ exercise, onChange, locked }: ExerciseProps<"match_pairs">) {
  const pairs = exercise.payload.pairs;
  const left = useMemo(() => shuffled(pairs.map((p) => p[0]), exercise.id), [pairs, exercise.id]);
  const right = useMemo(() => shuffled(pairs.map((p) => p[1]), exercise.id + 7), [pairs, exercise.id]);
  const [sel, setSel] = useState<{ side: 0 | 1; word: string } | null>(null);
  const [matched, setMatched] = useState<[string, string][]>([]);
  const [flash, setFlash] = useState<{ words: string[]; good: boolean } | null>(null);

  // Source of truth for taps: updated immediately, so fast tapping can't lose or repeat a match
  // (the state copy only catches up after the flash animation).
  const found = useRef<[string, string][]>([]);
  const isMatched = (side: 0 | 1, w: string) => matched.some((m) => m[side] === w);

  function tap(side: 0 | 1, word: string) {
    if (locked || found.current.some((m) => m[side] === word)) return;
    if (side === 0) speak(word);
    if (!sel || sel.side === side) return setSel({ side, word });
    const pair: [string, string] = side === 0 ? [word, sel.word] : [sel.word, word];
    const good = pairs.some((p) => p[0] === pair[0] && p[1] === pair[1]);
    setSel(null);
    setFlash({ words: pair, good });
    if (good) { sfx.tap(); found.current = [...found.current, pair]; } else { sfx.wrong(); }
    const all = found.current;
    setTimeout(() => {
      setFlash(null);
      if (!good) return;
      setMatched(all);
      if (all.length === pairs.length) onChange(all);
    }, good ? 350 : 500);
  }

  const cls = (side: 0 | 1, w: string) => [
    s.option,
    isMatched(side, w) && s.matched,
    sel?.side === side && sel.word === w && s.selected,
    flash?.words[side] === w && (flash.good ? s.flashGood : s.flashBad),
  ].filter(Boolean).join(" ");

  return (
    <div className={s.pairs}>
      {([left, right] as const).map((col, side) => (
        <div key={side}>
          {col.map((w, i) => (
            <button key={w} className={cls(side as 0 | 1, w)} onClick={() => tap(side as 0 | 1, w)}>
              <span className={s.key}>{side * pairs.length + i + 1}</span>{w}
            </button>
          ))}
        </div>
      ))}
    </div>
  );
}
