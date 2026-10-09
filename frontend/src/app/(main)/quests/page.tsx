"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Chest, Lightning, Target } from "@/components/Icons";
import Mascot from "@/components/Mascot";
import { useApp } from "@/components/Providers";
import { api, ApiError, type Quest } from "@/lib/api";
import { sfx } from "@/lib/sound";
import s from "../pages.module.css";

const ICONS: Record<string, React.ReactNode> = { goal: <Lightning size={44} />, lessons: <span>📘</span>, perfect: <Target size={44} /> };

export default function QuestsPage() {
  const { me, setMe, toast } = useApp();
  const [quests, setQuests] = useState<Quest[] | null>(null);
  useEffect(() => { api.quests().then(setQuests).catch(() => {}); }, [me?.xp_total]);
  if (!me || !quests) return null;

  async function claim(code: string) {
    try {
      const r = await api.claimQuest(code);
      setMe(r.me);
      sfx.complete();
      toast({ icon: "🎁", title: `Chest opened: +${r.gems_earned} gems` });
      setQuests(await api.quests());
    } catch (e) { toast({ icon: "⚠️", title: (e as ApiError).message }); }
  }
  return (
    <div className={s.page}>
      <section className="card" style={{ display: "flex", alignItems: "center", gap: 20, background: "var(--beetle)", border: 0, color: "#fff" }}>
        <div style={{ flex: 1 }}>
          <h1 className={s.title} style={{ color: "#fff" }}>Daily Quests</h1>
          <p>Complete quests to earn rewards! Quests refresh every day.</p>
        </div>
        <Mascot size={90} mood="cheer" />
      </section>
      <section className="card">
        {quests.map((q) => (
          <div key={q.code} className={s.row}>
            <span className={s.iconBox}>{ICONS[q.code]}</span>
            <div className={s.grow}>
              <h3>{q.title}</h3>
              <div className="bar" style={{ ["--fill" as string]: "var(--bee)" }}><span style={{ width: `${(100 * q.progress) / q.target}%` }} /></div>
              <small className="muted">{q.progress} / {q.target} · 💎 {q.reward}</small>
            </div>
            {q.claimed ? <span className="muted" title="Opened">✅</span>
              : q.progress >= q.target ? <button className="btn gold small" onClick={() => claim(q.code)}><Chest size={22} /> Open</button>
              : <Chest size={40} />}
          </div>
        ))}
        <Link className="btn green block" href="/" style={{ marginTop: 12 }}>Start a lesson</Link>
      </section>
      <section className="card">
        <h2>Monthly challenge <span className="coming-soon">Coming soon</span></h2>
        <p className="muted">Complete 30 quests this month to earn an exclusive badge.</p>
      </section>
      <section className="card">
        <h2>Friends quest <span className="coming-soon">Coming soon</span></h2>
        <p className="muted">Team up with a friend to reach a shared goal.</p>
      </section>
    </div>
  );
}
