"use client";
import { useEffect, useRef, useState } from "react";
import { canRecognizeSpeech, recognize } from "@/lib/sound";
import SpeechBubble from "./SpeechBubble";
import type { ExerciseProps } from "./types";
import s from "../lesson.module.css";

/** Read the sentence aloud. The browser transcribes it; the server grades the transcript
 *  with a forgiving similarity match. Without speech recognition the player skips this type. */
export default function Speak({ exercise, onChange, locked }: ExerciseProps<"speak">) {
  const [state, setState] = useState<"idle" | "listening" | "heard" | "error">("idle");
  const [heard, setHeard] = useState("");
  const stop = useRef<(() => void) | null>(null);
  useEffect(() => () => stop.current?.(), []);

  async function toggle() {
    if (locked) return;
    if (state === "listening") return stop.current?.();
    setState("listening");
    const r = recognize();
    stop.current = r.stop;
    try {
      const text = await r.result;
      setHeard(text);
      setState(text ? "heard" : "idle");
      onChange(text || null);
    } catch {
      setState("error");
    }
  }

  return (
    <>
      <SpeechBubble tokens={exercise.payload.tokens} reading={exercise.payload.reading}
        translation={exercise.payload.translation} tts={exercise.tts} />
      <button className={`btn ghost block ${s.mic} ${state === "listening" ? s.recording : ""}`} onClick={toggle}
        disabled={locked || !canRecognizeSpeech()}>
        🎙️ {state === "listening" ? "Listening… tap to stop" : state === "heard" ? "Tap to try again" : "Tap to speak"}
      </button>
      {heard && <p className={s.hint}>We heard: “{heard}”</p>}
      {state === "error" && <p className={s.hint}>Microphone unavailable. Allow mic access, or tap &ldquo;Can&apos;t speak now&rdquo;.</p>}
    </>
  );
}
