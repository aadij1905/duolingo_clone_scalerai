import type { AnswerValue, Exercise } from "@/lib/api";

/** Contract every exercise widget implements: render `exercise`, report the
 *  learner's current answer via onChange (null = nothing to check yet). */
export type ExerciseProps<T extends Exercise["type"]> = {
  exercise: Extract<Exercise, { type: T }>;
  onChange: (value: AnswerValue | null) => void;
  locked: boolean; // true once the answer has been checked
};
