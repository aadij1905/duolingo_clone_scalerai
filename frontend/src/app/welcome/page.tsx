"use client";
// Onboarding: pick a language, pick a daily goal (Casual by default), then straight into lesson 1.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import GoogleButton from "@/components/GoogleButton";
import Mascot from "@/components/Mascot";
import { useApp } from "@/components/Providers";
import { api, ApiError, type CourseProgress } from "@/lib/api";
import AccountForm from "../(main)/settings/AccountForm";
import s from "../(main)/pages.module.css";

const GOALS = [[10, "Casual", "5 min / day"], [20, "Regular", "10 min / day"], [30, "Serious", "15 min / day"], [50, "Intense", "20 min / day"]] as const;

export default function WelcomePage() {
  const router = useRouter();
  const { me, setMe, refreshMe, toast } = useApp();
  const [courses, setCourses] = useState<CourseProgress[]>([]);
  const [course, setCourse] = useState<number | null>(null);
  const [goal, setGoal] = useState(10);
  const [step, setStep] = useState<"course" | "goal" | "signin">("course");
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (me) api.courses().then(setCourses).catch(() => {}); }, [me]);

  async function start() {
    if (!course) return;
    setBusy(true);
    try {
      setMe(await api.updateMe({ course_id: course, daily_goal_xp: goal, onboarded: true }));
      const first = (await api.path()).units[0].skills[0].id;
      router.push(`/lesson?skill=${first}&mode=lesson`);
    } catch (e) { toast({ icon: "⚠️", title: (e as ApiError).message }); setBusy(false); }
  }

  async function demo() {
    try { await api.demoLogin(); await refreshMe(); router.push("/"); }
    catch { toast({ icon: "⚠️", title: "The demo account is turned off on this server" }); }
  }

  if (!me) return <div className={s.center} style={{ minHeight: "100dvh", alignContent: "center" }}><Mascot mood="think" className="bounce" /></div>;
  return (
    <main className={s.welcome}>
      <div className={s.center}>
        <Mascot size={110} mood={step === "goal" ? "cheer" : "happy"} className="bounce" />
        <h1 className={s.title}>
          {step === "course" ? "What would you like to learn?" : step === "goal" ? "Pick a daily goal" : "Sign in"}
        </h1>
        {me.registered && <p className="muted">Signed in as <b>{me.google_email ?? me.username}</b>. Pick a course to begin.</p>}
      </div>

      {step === "course" && (
        <div className={s.pickGrid}>
          {courses.map((c) => (
            <button key={c.id} className={`${s.pick} ${course === c.id ? s.on : ""}`} onClick={() => setCourse(c.id)} aria-pressed={course === c.id}>
              <span style={{ fontSize: 56 }}>{c.flag}</span><b>{c.title}</b>
            </button>
          ))}
        </div>
      )}
      {step === "goal" && (
        <div className={s.goalList}>
          {GOALS.map(([xp, label, time]) => (
            <button key={xp} className={`${s.opt} ${goal === xp ? s.on : ""}`} onClick={() => setGoal(xp)} aria-pressed={goal === xp}>
              <b>{label}</b><span className="muted">{time} · {xp} XP</span>
            </button>
          ))}
        </div>
      )}
      {step === "signin" && <>
        <GoogleButton onDone={() => router.push("/")} />
        <AccountForm mode="login" onDone={async () => { await refreshMe(); router.push("/"); }} />
      </>}

      <div className={s.welcomeActions}>
        {step === "course" && <>
          <button className="btn green block" disabled={!course} onClick={() => setStep("goal")}>Continue</button>
          {!me.registered && <>
            <button className="btn ghost block" onClick={() => setStep("signin")}>I already have an account</button>
            <button className="btn ghost gray block" onClick={demo}>Explore the demo account</button>
            {/* A new Google account (or a guest linking Google) isn't onboarded yet, so it lands back here to pick a course. */}
            <GoogleButton onDone={() => router.push("/")} />
          </>}
        </>}
        {step === "goal" && <>
          <button className="btn green block" disabled={busy} onClick={start}>{busy ? "Starting…" : "Start lesson 1"}</button>
          <button className="btn ghost gray block" onClick={() => setStep("course")}>Back</button>
        </>}
        {step === "signin" && <button className="btn ghost gray block" onClick={() => setStep("course")}>Back</button>}
      </div>
    </main>
  );
}
