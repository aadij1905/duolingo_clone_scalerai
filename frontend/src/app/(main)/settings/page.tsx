"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useApp } from "@/components/Providers";
import { api, ApiError, type CourseProgress } from "@/lib/api";
import { playbackRate, RATES, setPlaybackRate, setSoundEnabled, soundEnabled, speak, voiceName } from "@/lib/sound";
import GoogleButton from "@/components/GoogleButton";
import AccountForm from "./AccountForm";
import s from "../pages.module.css";

type Theme = "system" | "light" | "dark";
const GOALS = [[10, "Casual"], [20, "Regular"], [30, "Serious"], [50, "Intense"]] as const;

function applyTheme(t: Theme) {
  try { if (t === "system") localStorage.removeItem("duo:theme"); else localStorage.setItem("duo:theme", t); } catch { /* storage blocked */ }
  if (t === "system") delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = t;
}

export default function SettingsPage() {
  const { me, setMe, refreshMe, toast } = useApp();
  const router = useRouter();
  // The page renders nothing until `me` loads (client-side), so reading browser state here can't cause a hydration mismatch.
  const [theme, setTheme] = useState<Theme>(() => (typeof document === "undefined" ? "system" : (document.documentElement.dataset.theme as Theme) ?? "system"));
  const [sound, setSound] = useState(() => typeof window === "undefined" || soundEnabled());
  const [draftName, setName] = useState<string | null>(null); // null = not edited yet
  const [rate, setRate] = useState(() => (typeof window === "undefined" ? 1 : playbackRate()));
  const [clock, setClock] = useState<{ now: string; offset_days: number } | null>(null);
  const [courses, setCourses] = useState<CourseProgress[]>([]);
  const [account, setAccount] = useState<null | "register" | "login">(null);

  const [voice, setVoice] = useState<string | null>(null);
  useEffect(() => { api.devClock().then(setClock).catch(() => {}); }, []);
  useEffect(() => { // voices load asynchronously
    const read = () => setVoice(voiceName());
    const t = setTimeout(read, 300);
    window.speechSynthesis?.addEventListener("voiceschanged", read);
    return () => { clearTimeout(t); window.speechSynthesis?.removeEventListener("voiceschanged", read); };
  }, [me?.course.id]);
  useEffect(() => { api.courses().then(setCourses).catch(() => {}); }, [me?.course.id]);
  if (!me) return null;
  const name = draftName ?? me.display_name;

  async function save(data: Parameters<typeof api.updateMe>[0], msg: string) {
    try { setMe(await api.updateMe(data)); toast({ icon: "✅", title: msg }); }
    catch (e) { toast({ icon: "⚠️", title: (e as ApiError).message }); }
  }
  async function travel(days: number, label: string) {
    setClock(await api.timeTravel(days));
    await refreshMe();
    toast({ icon: "⏩", title: `Jumped ${label} ahead`, body: "Streak and hearts were re-evaluated." });
  }
  async function reset() {
    await api.resetDemo();
    window.location.reload(); // fresh learner: reload so the app re-syncs timezone and every cached view
  }
  async function logout() {
    await api.logout();
    await refreshMe(); // becomes a fresh guest, who is sent to onboarding
    router.push("/");
  }

  return (
    <div className={s.page}>
      <h1 className={s.title}>Settings</h1>

      <section className="card">
        <h2>Preferences</h2>
        <div className={s.row}>
          <div className={s.grow}><h3>Sound effects</h3><span className="muted">Feedback sounds and pronunciation audio</span></div>
          <button role="switch" aria-checked={sound} aria-label="Sound effects" className={s.switch}
            onClick={() => { setSoundEnabled(!sound); setSound(!sound); }} />
        </div>
        <div className={s.row}>
          <div className={s.grow}>
            <h3>{me.course.title} voice</h3>
            <span className="muted">
              {voice ?? "No voice found"}. For the clearest audio use Chrome (its Google voices), or on a Mac download a
              Premium voice in System Settings → Accessibility → Spoken Content → System voice → Manage Voices.
            </span>
          </div>
          <button className="btn ghost small" onClick={() => speak({ es: "Hola, ¿cómo estás?", fr: "Bonjour, comment ça va ?", ja: "こんにちは、お元気ですか", hi: "नमस्ते, आप कैसे हैं?" }[me.course.language_code] ?? "")}>Test</button>
        </div>
        <div className={s.row}>
          <div className={s.grow}><h3>Audio speed</h3>
            <div className={s.options}>
              {RATES.map((r) => (
                <button key={r} className={`${s.opt} ${rate === r ? s.on : ""}`} onClick={() => { setPlaybackRate(r); setRate(r); }}>
                  {r === 1 ? "Normal" : r < 1 ? "Slower" : "Faster"}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className={s.row}>
          <div className={s.grow}><h3>Dark mode</h3>
            <div className={s.options}>
              {(["system", "light", "dark"] as Theme[]).map((t) => (
                <button key={t} className={`${s.opt} ${theme === t ? s.on : ""}`} onClick={() => { applyTheme(t); setTheme(t); }}>
                  {t[0].toUpperCase() + t.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className={s.row}>
          <div className={s.grow}><h3>Daily goal</h3>
            <div className={s.options}>
              {GOALS.map(([xp, label]) => (
                <button key={xp} className={`${s.opt} ${me.daily_goal_xp === xp ? s.on : ""}`} onClick={() => save({ daily_goal_xp: xp }, "Daily goal updated")}>
                  {label} · {xp} XP
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="card">
        <h2>Profile</h2>
        <form className={s.row} onSubmit={(e) => { e.preventDefault(); void save({ display_name: name.trim() }, "Name saved"); }}>
          <div className={s.grow}>
            <label htmlFor="name"><h3>Name</h3></label>
            <input id="name" className={s.input} value={name} maxLength={60} onChange={(e) => setName(e.target.value)} />
          </div>
          <button className="btn small" disabled={!name.trim() || name === me.display_name}>Save</button>
        </form>
        <div className={s.row}><div className={s.grow}><h3>Notifications</h3><span className="muted">Practice reminders by email and push</span></div><span className="coming-soon">Coming soon</span></div>
      </section>

      <section className="card">
        <h2>Courses</h2>
        <p className="muted">Each course keeps its own path. XP, streak, hearts and gems are shared.</p>
        {courses.map((c) => (
          <div key={c.id} className={s.row}>
            <span style={{ fontSize: 32 }}>{c.flag}</span>
            <div className={s.grow}><h3>{c.title}</h3><span className="muted">{c.skills_done} / {c.skills_total} skills · from English</span></div>
            {c.current ? <span className="muted">Current</span> : (
              <button className="btn ghost small" onClick={() => save({ course_id: c.id }, `Switched to ${c.title}`)}>Switch</button>
            )}
          </div>
        ))}
      </section>

      <section className="card">
        <h2>Account</h2>
        {me.registered ? (
          <div className={s.row}>
            <div className={s.grow}>
              <h3>{me.google_email ?? `@${me.username}`}</h3>
              <span className="muted">Signed in{me.google_email ? " with Google" : ""}. Your progress is saved to this account.</span>
            </div>
            <button className="btn ghost small" onClick={logout}>Sign out</button>
          </div>
        ) : (
          <>
            <p className="muted" style={{ marginBottom: 12 }}>
              You&apos;re learning as a guest on this browser. Create an account to keep your progress and use it on other devices.
            </p>
            <div style={{ marginBottom: 12 }}><GoogleButton onDone={() => {}} /></div>
            {account ? <AccountForm mode={account} onDone={async () => {
              setAccount(null);
              if (account === "login") { await refreshMe(); router.push("/"); }
            }} /> : (
              <div className={s.options}>
                <button className="btn green small" onClick={() => setAccount("register")}>Create account</button>
                <button className="btn ghost small" onClick={() => setAccount("login")}>I have an account</button>
              </div>
            )}
          </>
        )}
      </section>

      <section className="card">
        <h2>Demo controls</h2>
        <p className="muted">Simulate days passing to test streaks, Streak Freezes, leagues and heart regeneration. The server clock is shared by every learner.</p>
        {clock && <p style={{ margin: "10px 0" }}>Server date: <b>{new Date(clock.now).toUTCString().slice(0, 22)}</b> {clock.offset_days !== 0 && <span className="muted">(+{clock.offset_days.toFixed(1)} days)</span>}</p>}
        <div className={s.options}>
          <button className="btn ghost small" onClick={() => travel(1, "1 day")}>+1 day</button>
          <button className="btn ghost small" onClick={() => travel(2, "2 days")}>+2 days</button>
          <button className="btn ghost small" onClick={() => travel(1 / 24, "1 hour")}>+1 hour</button>
          <button className="btn red small" onClick={reset}>Reset my progress</button>
        </div>
      </section>
    </div>
  );
}
