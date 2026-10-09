"use client";
import { Fragment, useEffect, useState } from "react";
import { Shield } from "@/components/Icons";
import Mascot from "@/components/Mascot";
import { useApp } from "@/components/Providers";
import { api, type Leaderboard } from "@/lib/api";
import s from "../pages.module.css";

const LEAGUES = [["Bronze", "#cd7900"], ["Silver", "#c0c0c0"], ["Gold", "#ffc800"], ["Sapphire", "#1cb0f6"], ["Ruby", "#ff4b4b"]];
const MEDALS = ["🥇", "🥈", "🥉"];

function daysLeft(iso: string) {
  const ms = new Date(iso).getTime() - Date.now();
  const d = Math.floor(ms / 86400000);
  return d >= 1 ? `${d} day${d > 1 ? "s" : ""}` : `${Math.max(1, Math.floor(ms / 3600000))} hours`;
}

export default function LeaderboardPage() {
  const { me } = useApp();
  const [board, setBoard] = useState<Leaderboard | null>(null);
  useEffect(() => { api.leaderboard().then(setBoard).catch(() => {}); }, [me?.xp_total]);

  if (!board) return <div className={s.center}><Mascot mood="think" className="bounce" /></div>;
  const lastPromo = board.entries.filter((e) => e.zone === "promotion").at(-1)?.rank;
  const firstDemo = board.entries.find((e) => e.zone === "demotion")?.rank;

  return (
    <div className={s.page}>
      <div className={s.center} style={{ borderBottom: "2px solid var(--border)", paddingBottom: 20 }}>
        <div className={s.shields}>
          {LEAGUES.map(([name, color], i) => (
            <span key={name} className={i === board.tier ? s.current : ""}><Shield size={i === board.tier ? 72 : 52} color={color} /></span>
          ))}
        </div>
        <h1 className={s.title}>{board.league} League</h1>
        <p className="muted">{board.tier < LEAGUES.length - 1 ? "Top 7 advance to the next league" : "The top league: stay out of the bottom 5!"}</p>
        <b style={{ color: "var(--bee-dark)" }}>{daysLeft(board.ends_at)} left</b>
      </div>
      <ol className={s.board}>
        {board.entries.map((e) => (
          <Fragment key={e.user_id}>
            {e.rank === firstDemo && <li className={s.zone} style={{ color: "var(--cardinal)" }}>▼ Demotion zone ▼</li>}
            <li className={`${s.entry} ${e.is_me ? s.me : ""}`}>
              <span className={s.rank} style={{ color: e.zone === "promotion" ? "var(--feather)" : e.zone === "demotion" ? "var(--cardinal)" : undefined }}>
                {MEDALS[e.rank - 1] ?? e.rank}
              </span>
              <span className={s.avatar} style={{ background: e.avatar_color }}>{e.name[0]}</span>
              <span className="name" style={{ flex: 1, fontWeight: 800 }}>{e.is_me ? `${e.name} (you)` : e.name}</span>
              <span className="muted">{e.xp} XP</span>
            </li>
            {e.rank === lastPromo && <li className={s.zone} style={{ color: "var(--feather)" }}>▲ Promotion zone ▲</li>}
          </Fragment>
        ))}
      </ol>
      <p className="muted" style={{ textAlign: "center" }}>Friends & following <span className="coming-soon">Coming soon</span></p>
    </div>
  );
}
