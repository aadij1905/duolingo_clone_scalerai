import LessonPlayer from "@/components/LessonPlayer";
import type { Mode, PracticeKind } from "@/lib/api";

const MODES: Mode[] = ["lesson", "practice", "legendary"];
const KINDS: PracticeKind[] = ["mix", "listening", "speaking", "mistakes"];

// /lesson?skill=3&mode=lesson (or ?mode=practice&kind=listening) — full-screen player, outside the app chrome.
export default async function LessonPage({ searchParams }: PageProps<"/lesson">) {
  const q = await searchParams;
  const mode = MODES.includes(q.mode as Mode) ? (q.mode as Mode) : "lesson";
  const kind = KINDS.includes(q.kind as PracticeKind) ? (q.kind as PracticeKind) : "mix";
  const skill = Number(q.skill);
  return <LessonPlayer key={`${skill}-${mode}-${kind}`} skillId={Number.isFinite(skill) && skill > 0 ? skill : null} mode={mode} kind={kind} />;
}
