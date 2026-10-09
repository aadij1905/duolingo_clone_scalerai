"use client";
// The core lesson loop: answer -> CHECK -> feedback bar -> CONTINUE, until every
// exercise is answered correctly (missed ones are re-queued at the end, like
// Duolingo). The server grades each answer and owns hearts/XP; this component
// only renders state and sequences the screens.
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  api, ApiError, LISTENING, type AnswerResult, type AnswerValue, type Exercise, type LessonResult, type LessonSession,
  type Mode, type PracticeKind,
} from "@/lib/api";
import { canRecognizeSpeech, hasVoice, sfx, speak, soundEnabled } from "@/lib/sound";
import ExerciseView from "./exercises";
import { Check, Clock, Close, Flame, Gem, Heart, Lightning, Target } from "./Icons";
import Mascot from "./Mascot";
import Modal, { Confetti } from "./Modal";
import { useApp } from "./Providers";
import s from "./lesson.module.css";

const PRAISE = ["Nice job!", "Great!", "Excellent!", "Amazing!", "Correct!", "Awesome!"];
type Phase = "loading" | "answering" | "checking" | "feedback" | "finishing" | "done" | "streak";
type Blocker = null | "quit" | "hearts" | "time" | "legendary_failed" | "error";

// "Can't listen / speak now": that exercise type is skipped (no heart lost) for 15 minutes.
type Category = "listen" | "speak";
const MUTE_MS = 15 * 60 * 1000;
const categoryOf = (e: Exercise): Category | null => (LISTENING.includes(e.type) ? "listen" : e.type === "speak" ? "speak" : null);
function isMuted(c: Category) {
  if (c === "speak" && !canRecognizeSpeech()) return true; // e.g. Firefox: no speech recognition at all
  try { return Number(localStorage.getItem(`duo:mute:${c}`)) > Date.now(); } catch { return false; }
}

export default function LessonPlayer({ skillId, mode, kind = "mix" }: { skillId: number | null; mode: Mode; kind?: PracticeKind }) {
  const router = useRouter();
  const { me, setMe, refreshMe, toast } = useApp();
  const [session, setSession] = useState<LessonSession | null>(null);
  const [queue, setQueue] = useState<Exercise[]>([]);
  const [solved, setSolved] = useState(0);
  const [value, setValue] = useState<AnswerValue | null>(null);
  const [phase, setPhase] = useState<Phase>("loading");
  const [feedback, setFeedback] = useState<AnswerResult | null>(null);
  const [hearts, setHearts] = useState(5);
  const [mistakes, setMistakes] = useState(0);
  const [combo, setCombo] = useState(0);
  const [result, setResult] = useState<LessonResult | null>(null);
  const [blocker, setBlocker] = useState<Blocker>(null);
  const [errorMsg, setErrorMsg] = useState("");
  const [missed, setMissed] = useState<Set<number>>(new Set());
  const [attempt, setAttempt] = useState(0); // remounts the exercise widget for each new question
  const [now, setNow] = useState(() => Date.now());
  // Count down from the time limit on the *browser* clock; the server enforces its own deadline,
  // so client clock skew can't extend the challenge and server time-travel can't break the UI.
  const [deadline, setDeadline] = useState<number | null>(null);
  const started = useRef(false);
  const [praise, setPraise] = useState(PRAISE[0]);

  const current = queue[0];
  const total = session?.exercises.length ?? 1;

  // ---- start a server session once (guard against StrictMode double-mount)
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    api.startSession(skillId, mode, kind).then(async (s) => {
      // Muted kinds (or speaking without speech recognition) are skipped up front, except in their own practice.
      const muted = kind === "listening" || kind === "speaking" ? [] : s.exercises.filter((e) => {
        const c = categoryOf(e);
        return c && isMuted(c);
      });
      await Promise.all(muted.map((e) => api.answer(s.id, e.id, "", true)));
      setSession(s);
      setQueue(s.exercises.filter((e) => !muted.includes(e)));
      setSolved(muted.length);
      setHearts(s.hearts);
      if (s.time_limit_s) setDeadline(Date.now() + s.time_limit_s * 1000);
      setPhase("answering");
    }).catch((e: ApiError) => {
      if (e.code === "out_of_hearts") setBlocker("hearts");
      else { setErrorMsg(e.message); setBlocker("error"); }
    });
  }, [skillId, mode, kind]);

  // ---- read the prompt aloud when a new exercise appears (Duolingo autoplays audio)
  const category = current ? categoryOf(current) : null;
  useEffect(() => {
    if (current?.tts && phase === "answering" && soundEnabled()) speak(current.tts);
  }, [current, phase]);

  // ---- warn once if the system has no voice for this language (voices load asynchronously)
  const courseTitle = me?.course.title;
  useEffect(() => {
    if (!session || !courseTitle || typeof window === "undefined" || !("speechSynthesis" in window)) return;
    const check = () => {
      if (hasVoice() === false) toast({ icon: "🔇", title: `No ${courseTitle} voice on this device`, body: "Audio may not play. Add one in system settings, or tap \"Can't listen now\"." });
    };
    if (hasVoice() === null) window.speechSynthesis.addEventListener("voiceschanged", check, { once: true });
    else check();
  }, [session, courseTitle, toast]);

  // ---- legendary countdown
  useEffect(() => {
    if (!deadline || phase === "done" || phase === "streak") return;
    const t = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(t);
  }, [deadline, phase]);
  const remaining = deadline ? Math.max(0, Math.ceil((deadline - now) / 1000)) : null;
  const timeUp = remaining === 0 && !["done", "streak", "finishing"].includes(phase);
  const modal: Blocker = blocker ?? (timeUp ? "time" : null);

  const check = useCallback(async (answer: AnswerValue | null) => {
    if (!session || !current || phase !== "answering") return;
    setPhase("checking");
    try {
      const r = await api.answer(session.id, current.id, answer ?? (current.type === "match_pairs" ? [] : ""));
      setPraise(PRAISE[Math.floor(Math.random() * PRAISE.length)]);
      setFeedback(r);
      setHearts(r.hearts);
      setMistakes(r.mistakes);
      setCombo((c) => (r.correct ? c + 1 : 0));
      if (r.correct) { sfx.correct(); setSolved((n) => n + 1); } else { sfx.wrong(); setMissed((m) => new Set(m).add(current.id)); }
      setPhase("feedback");
    } catch (e) {
      const err = e as ApiError;
      if (err.code === "time_up") setBlocker("time");
      else { toast({ icon: "⚠️", title: err.message }); setPhase("answering"); }
    }
  }, [session, current, phase, toast]);

  const finish = useCallback(async () => {
    if (!session) return;
    setPhase("finishing");
    try {
      const r = await api.complete(session.id);
      setResult(r);
      sfx.complete();
      setPhase("done");
      void refreshMe();
      r.achievements.forEach((a) => toast({ icon: a.icon, title: `Achievement unlocked: ${a.title}`, body: a.description }));
      if (r.daily_goal_reached) toast({ icon: "🎯", title: "Daily goal reached!", body: "Bonus gems added to your total" });
    } catch (e) {
      const err = e as ApiError;
      if (err.code === "time_up") setBlocker("time");
      else { setErrorMsg(err.message); setBlocker("error"); }
    }
  }, [session, refreshMe, toast]);

  // "Can't listen / speak now": every remaining exercise of that kind is skipped. Skips count as
  // done and never cost a heart (the server only accepts them for listening/speaking types).
  async function cantDo(c: Category) {
    if (!session) return;
    try { localStorage.setItem(`duo:mute:${c}`, String(Date.now() + MUTE_MS)); } catch { /* storage blocked: this lesson only */ }
    setPhase("checking");
    const drop = queue.filter((e) => categoryOf(e) === c);
    try { await Promise.all(drop.map((e) => api.answer(session.id, e.id, "", true))); } catch (e) {
      toast({ icon: "⚠️", title: (e as ApiError).message });
      setPhase("answering");
      return;
    }
    toast({ icon: c === "listen" ? "🎧" : "🎙️", title: `${c === "listen" ? "Listening" : "Speaking"} exercises off for 15 minutes` });
    const rest = queue.filter((e) => categoryOf(e) !== c);
    setSolved((n) => n + drop.length);
    setQueue(rest);
    setValue(null);
    setAttempt((a) => a + 1);
    if (rest.length === 0) void finish();
    else setPhase("answering");
  }

  const next = useCallback(() => {
    if (!feedback || !current) return;
    if (feedback.status === "failed") {
      setBlocker(mode === "legendary" ? "legendary_failed" : "hearts");
      return;
    }
    // wrong answers come back at the end of the lesson
    const rest = feedback.correct ? queue.slice(1) : [...queue.slice(1), current];
    setQueue(rest);
    setValue(null);
    setFeedback(null);
    setAttempt((a) => a + 1);
    if (rest.length === 0) void finish();
    else setPhase("answering");
  }, [feedback, current, queue, mode, finish]);

  // ---- keyboard: Enter checks / continues
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Enter" || modal) return;
      if (phase === "answering" && value !== null) { e.preventDefault(); void check(value); }
      else if (phase === "feedback") { e.preventDefault(); next(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase, value, check, next, modal]);

  // Match pairs reports its answer only when all pairs are matched: check right away.
  const onChange = (v: AnswerValue | null) => {
    setValue(v);
    if (current?.type === "match_pairs" && v) void check(v);
  };

  async function refillAndRetry() {
    try {
      setMe(await api.refillHearts());
      window.location.reload(); // fresh session with full hearts
    } catch (e) { toast({ icon: "💎", title: (e as ApiError).message }); }
  }

  const exit = () => { void refreshMe(); router.push("/"); };

  // ------------------------------------------------------------------ render
  if (phase === "done" && result) return <LessonComplete result={result} onContinue={() => (result.streak_extended ? setPhase("streak") : exit())} />;
  if (phase === "streak" && result) return <StreakScreen streak={result.streak} onContinue={exit} />;

  const pct = (100 * solved) / total;
  const legendary = mode === "legendary";

  return (
    <div className={s.page}>
      <header className={s.header}>
        <button className={s.quit} onClick={() => setBlocker("quit")} aria-label="Quit lesson"><Close size={26} /></button>
        <div className={s.progress}>
          {combo >= 3 && <span key={combo} className={s.combo}>{combo} IN A ROW</span>}
          <div className="bar" role="progressbar" aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}
            style={legendary ? { ["--fill" as string]: "var(--beetle)" } : undefined}>
            <span style={{ width: `${pct}%` }} />
          </div>
        </div>
        {legendary ? (
          <>
            <span className={`${s.timer} ${remaining !== null && remaining <= 15 ? s.low : ""}`}><Clock /> {remaining !== null ? `${Math.floor(remaining / 60)}:${String(remaining % 60).padStart(2, "0")}` : "--"}</span>
            <span className={s.hearts} title="Mistakes left"><Heart muted={mistakes > (session?.max_mistakes ?? 3)} /> {Math.max(0, (session?.max_mistakes ?? 3) - mistakes)}</span>
          </>
        ) : mode === "practice" || session?.no_heart_loss ? (
          <span className={s.hearts} style={{ color: "var(--macaw)" }} title={session?.no_heart_loss ? "Mistakes are free" : "Practice"}>{session?.no_heart_loss ? "🛡️" : "🏋️"}</span>
        ) : (
          <span className={`${s.hearts} ${feedback && !feedback.correct ? "shake" : ""}`} key={hearts}><Heart /> {hearts}</span>
        )}
      </header>

      <main className={s.body}>
        {phase === "loading" && !blocker && <div style={{ margin: "auto" }}><Mascot mood="think" className="bounce" /></div>}
        {current && phase !== "loading" && (
          <>
            {legendary && <span className={s.badge}>👑 Legendary</span>}
            {session?.no_heart_loss && <span className={s.badge} style={{ color: "var(--feather-dark)" }}>🛡️ Warm-up lesson: mistakes won&apos;t cost hearts</span>}
            {missed.has(current.id) && !feedback && <span className={s.badge} style={{ color: "var(--fox)" }}>↻ Previous mistake</span>}
            <h1 className={s.prompt}>{current.prompt}</h1>
            <ExerciseView key={attempt} exercise={current} onChange={onChange} locked={phase !== "answering"} />
          </>
        )}
      </main>

      {phase !== "loading" && (
        <footer className={`${s.footer} ${feedback ? (feedback.correct ? s.correct : s.wrong) : ""}`}>
          <div className={s.footerInner}>
            {feedback ? (
              <>
                <div className={s.verdict} role="alert">
                  <span className={s.verdictIcon}>{feedback.correct ? <Check size={40} /> : <Close size={36} />}</span>
                  <div>
                    <h2>{feedback.correct ? (feedback.typo ? "Watch out for typos!" : praise) : "Correct solution:"}</h2>
                    {(!feedback.correct || feedback.typo) && <p>{feedback.solution}</p>}
                    {feedback.reading && <p className={s.pron}>/{feedback.reading}/</p>}
                    {feedback.meaning && <p className={s.meaning}>Meaning: {feedback.meaning}</p>}
                  </div>
                </div>
                <button className={`btn ${feedback.correct ? "green" : "red"}`} onClick={next} autoFocus>Continue</button>
              </>
            ) : (
              <>
                {category ? (
                  <button className="btn ghost gray" onClick={() => cantDo(category)} disabled={phase !== "answering"}>
                    {category === "listen" ? "Can't listen now" : "Can't speak now"}
                  </button>
                ) : (
                  <button className={`btn ghost gray ${s.skip}`} onClick={() => check(null)} disabled={phase !== "answering"}>Skip</button>
                )}
                <button className="btn green" onClick={() => check(value)} disabled={value === null || phase !== "answering"}>
                  {phase === "finishing" ? "Saving…" : "Check"}
                </button>
              </>
            )}
          </div>
        </footer>
      )}

      {modal === "quit" && (
        <Modal label="Quit lesson" onClose={() => setBlocker(null)}>
          <Mascot mood="sad" size={110} />
          <h2>Wait, don&apos;t go!</h2>
          <p className="muted">You&apos;ll lose your progress if you quit now.</p>
          <button className="btn block" onClick={() => setBlocker(null)}>Keep learning</button>
          <button className="btn ghost gray block" style={{ ["--fg" as string]: "var(--cardinal)" }} onClick={exit}>End session</button>
        </Modal>
      )}
      {modal === "hearts" && (
        <Modal label="Out of hearts">
          <Mascot mood="sad" size={110} />
          <h2>You ran out of hearts!</h2>
          <p className="muted">Practice to earn hearts back, refill with gems, or wait for them to regenerate.</p>
          <button className="btn block" onClick={refillAndRetry} disabled={!me || me.gems < me.heart_refill_cost}>Refill <Gem size={20} /> {me?.heart_refill_cost}</button>
          <button className="btn ghost block" onClick={() => router.push("/lesson?mode=practice")}>Practice to earn hearts</button>
          <button className="btn ghost gray block" onClick={exit}>No thanks</button>
        </Modal>
      )}
      {(modal === "time" || modal === "legendary_failed") && (
        <Modal label="Challenge failed">
          <Mascot mood="sad" size={110} />
          <h2>{modal === "time" ? "Time's up!" : "Too many mistakes"}</h2>
          <p className="muted">Legendary challenges are tough. Review and try again!</p>
          <button className="btn purple block" onClick={() => window.location.reload()}>Try again</button>
          <button className="btn ghost gray block" onClick={exit}>Back to path</button>
        </Modal>
      )}
      {modal === "error" && (
        <Modal label="Error" onClose={exit}>
          <Mascot mood="think" size={110} />
          <h2>Hmm, that didn&apos;t work</h2>
          <p className="muted">{errorMsg}</p>
          <button className="btn block" onClick={exit}>Back to path</button>
        </Modal>
      )}
    </div>
  );
}

function LessonComplete({ result, onContinue }: { result: LessonResult; onContinue: () => void }) {
  const mins = `${Math.floor(result.duration_s / 60)}:${String(result.duration_s % 60).padStart(2, "0")}`;
  const title = result.mode === "legendary" ? "Legendary!" : result.mode === "practice" ? "Practice complete!" : result.perfect ? "Perfect lesson!" : "Lesson complete!";
  return (
    <div className={s.page}>
      <Confetti />
      <main className={s.end}>
        <Mascot mood="cheer" size={170} className="bounce" />
        <h1>{title}</h1>
        {result.mode === "practice" && <p className="muted">You earned back a heart ❤️</p>}
        <div className={s.statCards}>
          <div className={s.statCard} style={{ ["--c" as string]: "var(--bee)" }}><small>Total XP</small><div><Lightning size={22} /> {result.xp_earned}</div></div>
          <div className={s.statCard} style={{ ["--c" as string]: "var(--feather)", animationDelay: ".15s" }}><small>{result.accuracy === 100 ? "Amazing" : "Good"}</small><div><Target size={22} /> {result.accuracy}%</div></div>
          <div className={s.statCard} style={{ ["--c" as string]: "var(--macaw)", animationDelay: ".3s" }}><small>{result.duration_s < 120 ? "Speedy" : "Committed"}</small><div><Clock size={22} /> {mins}</div></div>
        </div>
        <p className="muted">+{result.gems_earned} gems · Daily goal {Math.min(result.daily_xp, result.daily_goal_xp)}/{result.daily_goal_xp} XP</p>
      </main>
      <footer className={s.footer}><div className={s.footerInner} style={{ justifyContent: "flex-end" }}>
        <button className="btn green" onClick={onContinue} autoFocus>Continue</button>
      </div></footer>
    </div>
  );
}

function StreakScreen({ streak, onContinue }: { streak: number; onContinue: () => void }) {
  const days = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"];
  const today = (new Date().getDay() + 6) % 7;
  return (
    <div className={s.page}>
      <main className={s.end}>
        <span className={`${s.bigFlame} bounce`}><Flame size={140} /></span>
        <div className={s.streakNum}>{streak}</div>
        <h1 style={{ color: "var(--fox)" }}>day streak!</h1>
        <div className={s.week}>
          {days.map((d, i) => (
            <span key={d}>{d}<i className={i <= today && today - i < streak ? s.on : ""}>{i <= today && today - i < streak ? "✓" : ""}</i></span>
          ))}
        </div>
        <p className="muted">Practice each day so your streak won&apos;t reset!</p>
      </main>
      <footer className={s.footer}><div className={s.footerInner} style={{ justifyContent: "flex-end" }}>
        <button className="btn green" onClick={onContinue} autoFocus>Continue</button>
      </div></footer>
    </div>
  );
}
