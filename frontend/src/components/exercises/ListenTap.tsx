"use client";
import { ListenButtons, WordBank } from "./parts";
import type { ExerciseProps } from "./types";

/** Hear it, then build it from tiles. */
export default function ListenTap({ exercise, onChange, locked }: ExerciseProps<"listen_tap">) {
  return (
    <>
      <ListenButtons text={exercise.tts ?? ""} reading={exercise.reading} />
      <WordBank words={exercise.payload.words} onChange={onChange} locked={locked} />
    </>
  );
}
