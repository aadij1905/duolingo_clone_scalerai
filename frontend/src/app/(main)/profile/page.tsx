"use client";
import { useEffect, useState } from "react";
import { Crown, Flame, Lightning, Shield, Target, Trophy } from "@/components/Icons";
import Mascot from "@/components/Mascot";
import { useApp } from "@/components/Providers";
import { api, type Profile } from "@/lib/api";
import s from "../pages.module.css";

export default function ProfilePage() {
  const { me } = useApp();
  const [p, setP] = useState<Profile | null>(null);
  useEffect(() => { api.profile().then(setP).catch(() => {}); }, [me?.xp_total, me?.display_name]);

  if (!p) return <div className={s.center}><Mascot mood="think" className="bounce" /></div>;
  const maxXp = Math.max(...p.weekly_xp.map((d) => d.xp), 1);
  const unlocked = p.achievements.filter((a) => a.unlocked_at).length;
  const stats = [
    { icon: <Flame size={30} />, value: p.stats.streak, label: "Day streak" },
    { icon: <Lightning size={30} />, value: p.stats.xp_total, label: "Total XP" },
    { icon: <Shield size={30} />, value: p.user.league, label: "Current league" },
    { icon: <Crown size={30} />, value: p.stats.skills_done, label: "Skills completed" },
    { icon: <Target size={30} />, value: p.stats.lessons_done, label: "Lessons completed" },
    { icon: <Trophy size={30} className="" />, value: p.stats.longest_streak, label: "Longest streak" },
  ];

  return (
    <div className={s.page}>
      <div className={s.profileHead}>
        <div className={s.bigAvatar} style={{ background: p.user.avatar_color }}>{p.user.display_name[0]}</div>
        <div style={{ display: "grid", gap: 4 }}>
          <h1 className={s.title}>{p.user.display_name}</h1>
          <span className="muted">@{p.user.username}</span>
          <span className="muted">Joined {new Date(p.joined).toLocaleDateString(undefined, { month: "long", year: "numeric" })}</span>
          <span style={{ fontSize: 28 }} title={`Learning ${p.user.course.title}`}>{p.user.course.flag}</span>
        </div>
      </div>

      <section>
        <h2 style={{ marginBottom: 14 }}>Statistics</h2>
        <div className={s.statsGrid}>
          {stats.map((st) => (
            <div key={st.label} className={s.stat}>{st.icon}<div><b>{st.value}</b><small>{st.label}</small></div></div>
          ))}
        </div>
      </section>

      <StreakCalendar today={p.user.today} practiced={p.practiced_days} />

      <section className="card">
        <h2>XP this week</h2>
        <div className={s.chart}>
          {p.weekly_xp.map((d) => (
            <div key={d.date}>
              <i style={{ height: `${(100 * d.xp) / maxXp}%` }} title={`${d.xp} XP`} />
              <small>{d.xp}</small>
              <small>{new Date(d.date + "T00:00").toLocaleDateString(undefined, { weekday: "short" })}</small>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h2>Achievements <span className="muted" style={{ fontSize: 15 }}>{unlocked}/{p.achievements.length}</span></h2>
        <div className={s.badges}>
          {p.achievements.map((a) => (
            <div key={a.code} className={s.row}>
              <span className={`${s.badge} ${a.unlocked_at ? "" : s.locked}`} style={{ background: a.color }}>{a.icon}</span>
              <div className={s.grow}>
                <h3>{a.title}</h3>
                <span className="muted">{a.description}</span>
                {a.unlocked_at && <small style={{ color: "var(--feather-dark)" }}>Unlocked {new Date(a.unlocked_at).toLocaleDateString()}</small>}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

/** This month, with practiced days (from the XP ledger) filled in. */
function StreakCalendar({ today, practiced }: { today: string; practiced: string[] }) {
  const [y, m] = today.split("-").map(Number);
  const first = new Date(y, m - 1, 1);
  const days = new Date(y, m, 0).getDate();
  const lead = (first.getDay() + 6) % 7; // Monday-first grid
  const done = new Set(practiced);
  const iso = (d: number) => `${y}-${String(m).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  return (
    <section className="card">
      <h2>{first.toLocaleDateString(undefined, { month: "long", year: "numeric" })} <span className="muted" style={{ fontSize: 15 }}>{practiced.length} days practiced</span></h2>
      <div className={s.calendar}>
        {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => <b key={i}>{d}</b>)}
        {Array.from({ length: lead }, (_, i) => <i key={`pad${i}`} />)}
        {Array.from({ length: days }, (_, i) => i + 1).map((d) => (
          <span key={d} className={`${done.has(iso(d)) ? s.practiced : ""} ${iso(d) === today ? s.today : ""}`}
            aria-label={`${iso(d)}${done.has(iso(d)) ? ", practiced" : ""}`}>{d}</span>
        ))}
      </div>
    </section>
  );
}
