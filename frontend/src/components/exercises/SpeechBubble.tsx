"use client";
import type { Token } from "@/lib/api";
import { speak } from "@/lib/sound";
import Mascot from "../Mascot";
import { Speaker } from "../Icons";
import { HintText } from "./parts";
import s from "../lesson.module.css";

/** Mascot "saying" a sentence: plain text (English) or hinted target-language tokens.
 *  The speaker button reads it aloud. */
export default function SpeechBubble({ text, tokens, reading, translation, tts }: {
  text?: string; tokens?: Token[]; reading?: string | null; translation?: string; tts?: string | null;
}) {
  return (
    <div className={s.speech}>
      <Mascot size={96} />
      <div className={s.bubble}>
        {tts && <button className={s.speak} onClick={() => speak(tts)} aria-label="Play audio"><Speaker /></button>}
        {tokens ? <HintText tokens={tokens} reading={reading} translation={translation} /> : <span>{text}</span>}
      </div>
    </div>
  );
}
