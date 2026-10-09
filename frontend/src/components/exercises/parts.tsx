"use client";
// Pieces shared by several exercise widgets.
import { useState } from "react";
import type { Token } from "@/lib/api";
import { sfx, speak } from "@/lib/sound";
import { Speaker } from "../Icons";
import { useApp } from "../Providers";
import s from "../lesson.module.css";

const OPENING = /^[¿¡«"]+$/;
const CLOSING = /^[.,!?;:»"]+$/;

/** Target-language text where every word shows its translation on hover / tap
 *  (and is read aloud on tap). Japanese tokens are joined without spaces. */
export function HintText({ tokens, reading, translation, className }: {
  tokens: Token[]; reading?: string | null; translation?: string; className?: string;
}) {
  const spaced = useApp().me?.course.word_spacing ?? true;
  return (
    <span className={className}>
      <span className={s.hintLine}>
        {tokens.map((tok, i) => {
          const gap = spaced && i > 0 && !CLOSING.test(tok.t) && !OPENING.test(tokens[i - 1].t) ? " " : "";
          return (
            <span key={i}>
              {gap}
              {tok.h ? (
                <span className={s.word} tabIndex={0} onClick={() => speak(tok.t)}>
                  {tok.t}<span className={s.tip} role="tooltip">{tok.h}</span>
                </span>
              ) : tok.t}
            </span>
          );
        })}
      </span>
      {reading && <small className={s.reading}>/{reading}/</small>}
      {translation && <small className={s.translation}>{translation}</small>}
    </span>
  );
}

/** Big speaker + 🐢 slow replay, for listening exercises, with the pronunciation underneath. */
export function ListenButtons({ text, reading }: { text: string; reading?: string | null }) {
  return (
    <div className={s.listenWrap}>
      <div className={s.listen}>
        <button className={`${s.listenBtn} btn`} onClick={() => speak(text)} aria-label="Play audio"><Speaker size={44} /></button>
        <button className={`${s.listenBtn} ${s.slow} btn`} onClick={() => speak(text, true)} aria-label="Play slowly">🐢</button>
      </div>
      {reading && <span className={s.listenReading}>/{reading}/</span>}
    </div>
  );
}

/** Tap tiles to build an answer; tap again to send them back. Reports the words joined by spaces. */
export function WordBank({ words, onChange, locked, speakTiles = false }: {
  words: string[]; onChange: (v: string | null) => void; locked: boolean; speakTiles?: boolean;
}) {
  const [chosen, setChosen] = useState<number[]>([]); // indexes into `words` (words can repeat)
  const update = (next: number[], tapped?: number) => {
    if (locked) return;
    if (speakTiles && tapped !== undefined) speak(words[tapped]); else sfx.tap();
    setChosen(next);
    onChange(next.length ? next.map((i) => words[i]).join(" ") : null);
  };
  return (
    <>
      <div className={s.answerLine} aria-label="Your answer">
        {chosen.map((i) => (
          <button key={i} className={s.tile} onClick={() => update(chosen.filter((c) => c !== i))}>{words[i]}</button>
        ))}
      </div>
      <div className={s.bank} aria-label="Word bank">
        {words.map((w, i) => (
          <button key={i} className={`${s.tile} ${chosen.includes(i) ? s.used : ""}`} aria-hidden={chosen.includes(i)}
            onClick={() => update([...chosen, i], i)}>{w}</button>
        ))}
      </div>
    </>
  );
}

/** Free-text answer box; Enter is "Check" (handled by the player). */
export function AnswerBox({ placeholder, onChange, locked }: { placeholder: string; onChange: (v: string | null) => void; locked: boolean }) {
  const [text, setText] = useState("");
  return (
    <textarea
      className={s.textarea} value={text} readOnly={locked} autoFocus maxLength={300}
      placeholder={placeholder} aria-label={placeholder} spellCheck={false} autoCapitalize="off" autoCorrect="off"
      onChange={(e) => { setText(e.target.value); onChange(e.target.value.trim() ? e.target.value : null); }}
      onKeyDown={(e) => { if (e.key === "Enter") e.preventDefault(); }}
    />
  );
}
