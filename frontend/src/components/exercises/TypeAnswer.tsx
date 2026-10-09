"use client";
import SpeechBubble from "./SpeechBubble";
import { AnswerBox } from "./parts";
import type { ExerciseProps } from "./types";

/** Free-text translation. The server ignores case, accents and punctuation, and forgives one typo. */
export default function TypeAnswer({ exercise, onChange, locked }: ExerciseProps<"type_answer">) {
  return (
    <>
      <SpeechBubble text={exercise.payload.text} />
      <AnswerBox placeholder={exercise.payload.placeholder} onChange={onChange} locked={locked} />
    </>
  );
}
