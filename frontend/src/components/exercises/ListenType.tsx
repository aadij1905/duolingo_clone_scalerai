"use client";
import { AnswerBox, ListenButtons } from "./parts";
import type { ExerciseProps } from "./types";

/** Hear it, then type it (Japanese accepts kana, kanji or romaji). */
export default function ListenType({ exercise, onChange, locked }: ExerciseProps<"listen_type">) {
  return (
    <>
      <ListenButtons text={exercise.tts ?? ""} reading={exercise.reading} />
      <AnswerBox placeholder={exercise.payload.placeholder} onChange={onChange} locked={locked} />
    </>
  );
}
