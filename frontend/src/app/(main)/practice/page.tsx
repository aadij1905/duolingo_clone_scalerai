"use client";
import Link from "next/link";
import { useEffect, useState, useSyncExternalStore } from "react";
import { Dumbbell, Heart, Trophy } from "@/components/Icons";
import Mascot from "@/components/Mascot";
import { api, type PathSkill } from "@/lib/api";
import { canRecognizeSpeech } from "@/lib/sound";
import s from "../pages.module.css";

export default function PracticePage() {
  const [completed, setCompleted] = useState<PathSkill[]>([]);
  const speech = useSyncExternalStore(() => () => {}, canRecognizeSpeech, () => true); // server: assume yes
  useEffect(() => {
    api.path().then((p) => setCompleted(p.units.flatMap((u) => u.skills).filter((sk) => sk.state === "completed"))).catch(() => {});
  }, []);

  return (
    <div className={s.page}>
      <section className="card" style={{ display: "flex", gap: 20, alignItems: "center", background: "var(--macaw)", border: 0, color: "#fff" }}>
        <div style={{ flex: 1 }}>
          <h1 className={s.title} style={{ color: "#fff" }}>Practice Hub</h1>
          <p>Review what you&apos;ve learned. Practice never costs hearts and earns one back!</p>
        </div>
        <Mascot size={90} mood="cheer" />
      </section>

      <section className="card">
        <div className={s.row}>
          <span className={s.iconBox} style={{ color: "var(--macaw)" }}><Dumbbell size={48} /></span>
          <div className={s.grow}>
            <h3>Personalized practice</h3>
            <span className="muted">8 exercises from lessons you&apos;ve finished. +10 XP and <Heart size={14} /> +1</span>
          </div>
          <Link className="btn" href="/lesson?mode=practice">Start</Link>
        </div>
        <div className={s.row}>
          <span className={s.iconBox}>🔁</span>
          <div className={s.grow}><h3>Mistakes review</h3><span className="muted">Retry the questions you missed most recently</span></div>
          <Link className="btn" href="/lesson?mode=practice&kind=mistakes">Start</Link>
        </div>
        <div className={s.row}>
          <span className={s.iconBox}>🎧</span>
          <div className={s.grow}><h3>Listening</h3><span className="muted">8 exercises: tap or type what you hear</span></div>
          <Link className="btn" href="/lesson?mode=practice&kind=listening">Start</Link>
        </div>
        <div className={s.row}>
          <span className={s.iconBox}>🎙️</span>
          <div className={s.grow}>
            <h3>Speaking</h3>
            <span className="muted">{speech ? "8 exercises: read words and sentences aloud" : "Your browser has no speech recognition. Try Chrome, Edge or Safari."}</span>
          </div>
          {speech ? <Link className="btn" href="/lesson?mode=practice&kind=speaking">Start</Link> : <span className="coming-soon">Unavailable</span>}
        </div>
      </section>

      <section className="card">
        <h2><Trophy size={24} /> Legendary challenges</h2>
        <p className="muted" style={{ marginBottom: 8 }}>
          Timed challenge: 10 questions, {Math.floor(150 / 60)}:30 on the clock, no more than 3 mistakes. Doesn&apos;t use hearts. +40 XP.
        </p>
        {completed.length === 0 && <p className="muted">Complete a skill to unlock its Legendary challenge.</p>}
        {completed.map((sk) => (
          <div key={sk.id} className={s.row}>
            <span className={s.iconBox}>{sk.icon}</span>
            <div className={s.grow}><h3>{sk.title}</h3>{sk.legendary && <small style={{ color: "var(--bee-dark)" }}>👑 Legendary</small>}</div>
            <Link className="btn gold small" href={`/lesson?skill=${sk.id}&mode=legendary`}>{sk.legendary ? "Replay" : "Start"}</Link>
          </div>
        ))}
      </section>
    </div>
  );
}
