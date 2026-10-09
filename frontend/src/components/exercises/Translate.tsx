"use client";
import SpeechBubble from "./SpeechBubble";
import { WordBank } from "./parts";
import type { ExerciseProps } from "./types";

/** Word bank translation, either direction. Target-language sentences carry word hints. */
export default function Translate({ exercise, onChange, locked }: ExerciseProps<"translate">) {
  const { tokens, sentence, reading, words, target } = exercise.payload;
  return (
    <>
      <SpeechBubble text={sentence} tokens={tokens} reading={reading} tts={exercise.tts} />
      <WordBank words={words} onChange={onChange} locked={locked} speakTiles={target} />
    </>
  );
}
