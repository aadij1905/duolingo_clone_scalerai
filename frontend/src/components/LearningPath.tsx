"use client";
// The home "path": units as colored banners, skills as zigzagging round nodes.
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, type Guidebook as GuidebookData, type LearningPath as Path, type PathSkill, type PathUnit } from "@/lib/api";
import { speak } from "@/lib/sound";
import { Check, Crown, Lock, Speaker, Star, Trophy } from "./Icons";
import Mascot from "./Mascot";
import Modal from "./Modal";
import { useApp } from "./Providers";
import s from "./path.module.css";

const ZIGZAG = [0, -45, -70, -45, 0, 45, 70, 45]; // horizontal offsets (px) that make the winding path

function ProgressRing({ done, total, color }: { done: number; total: number; color: string }) {
  const r = 45, c = 2 * Math.PI * r;
  return (
    <svg className={s.ring} viewBox="0 0 98 98" aria-hidden>
      <circle cx="49" cy="49" r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
      <circle cx="49" cy="49" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
        strokeDasharray={c} strokeDashoffset={c * (1 - done / total)} transform="rotate(-90 49 49)"
        style={{ transition: "stroke-dashoffset .6s" }} />
    </svg>
  );
}

function SkillNode({ skill, index, open, onToggle, color }: {
  skill: PathSkill; index: number; open: boolean; onToggle: () => void; color: string;
}) {
  const router = useRouter();
  const go = (mode: string) => router.push(`/lesson?skill=${skill.id}&mode=${mode}`); // the server checks hearts
  const isActive = skill.state === "active";
  const cls = `${s.node} ${skill.state === "locked" ? s.locked : ""} ${skill.legendary ? s.legendary : ""}`;
  // Locked / legendary nodes keep their grey / gold from CSS (an inline --n would override the class).
  const nodeColor = skill.state === "locked" || skill.legendary ? undefined : { ["--n" as string]: color, ["--n-dark" as string]: `color-mix(in srgb, ${color} 75%, black)` };
  const offset = ZIGZAG[index % ZIGZAG.length];

  return (
    // Each node's transform makes its own stacking context, so the open one is lifted above its neighbours.
    <div className={s.nodeWrap} style={{ transform: `translateX(${offset}px)`, zIndex: open ? 16 : undefined }} data-active={isActive || undefined}>
      {isActive && <ProgressRing done={skill.lessons_completed} total={skill.lessons_total} color={color} />}
      {isActive && !open && <div className={`${s.start} bounce`}>{skill.lessons_completed ? "Continue" : "Start"}</div>}
      <button className={cls} style={nodeColor} onClick={onToggle} aria-expanded={open}
        aria-label={`${skill.title}: ${skill.state}, ${skill.lessons_completed} of ${skill.lessons_total} lessons`}>
        {skill.state === "locked" ? <Lock /> : skill.legendary ? <Trophy size={34} /> : skill.state === "completed" ? <Check size={34} /> : <Star size={34} />}
        {skill.state === "completed" && <span className={s.crowns}><Crown size={22} /></span>}
      </button>
      <span className={s.label}>{skill.icon} {skill.title}</span>

      {open && (
        <div data-popover className={`${s.pop} ${skill.state === "locked" ? s.lockedPop : ""}`}
          style={{ ["--u" as string]: color, ["--off" as string]: `${offset}px` }}>
          <h3>{skill.title}</h3>
          {skill.state === "locked" && <>
            <p>Complete all levels above to unlock this!</p>
            <button className="btn block" disabled>Locked</button>
          </>}
          {skill.state === "active" && <>
            <p>Lesson {skill.lessons_completed + 1} of {skill.lessons_total}</p>
            <button className={s.popBtn} onClick={() => go("lesson")}>Start +10 XP</button>
          </>}
          {skill.state === "completed" && <>
            <p>{skill.legendary ? "Legendary! You've mastered this skill." : "Prove your proficiency with Legendary"}</p>
            <button className={s.popBtn} onClick={() => go("lesson")}>Review +10 XP</button>
            <button className={`${s.popBtn} ${s.gold}`} onClick={() => go("legendary")}>
              {skill.legendary ? "Replay legendary" : "Legendary"} +40 XP
            </button>
          </>}
        </div>
      )}
    </div>
  );
}

function Guidebook({ unitId, onClose }: { unitId: number; onClose: () => void }) {
  const [book, setBook] = useState<GuidebookData | null>(null);
  useEffect(() => { api.guidebook(unitId).then(setBook).catch(() => {}); }, [unitId]);
  return (
    <Modal label="Guidebook" onClose={onClose}>
      {!book ? <Mascot mood="think" className="bounce" /> : (
        <div className={s.book}>
          <small>Unit {book.position} guidebook</small>
          <h2>{book.title}</h2>
          <p className="muted">{book.description}</p>
          {book.skills.map((sk) => (
            <section key={sk.title}>
              <h3>{sk.icon} {sk.title}</h3>
              {(["word", "sentence"] as const).map((kind) => (
                <ul key={kind} className={kind === "word" ? s.bookWords : undefined}>
                  {sk.phrases.filter((p) => p.kind === kind).map((p) => (
                    <li key={p.text}>
                      <button className={s.bookSpeak} onClick={() => speak(p.text)} aria-label={`Play ${p.text}`}><Speaker size={18} /></button>
                      <span>
                        <b>{p.emoji} {p.text}</b>
                        {p.reading && <small className="muted"> {p.reading}</small>}
                        <span className="muted"> · {p.translation}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              ))}
            </section>
          ))}
        </div>
      )}
      <button className="btn block" onClick={onClose}>Got it</button>
    </Modal>
  );
}

function Unit({ unit, openId, setOpenId }: { unit: PathUnit; openId: number | null; setOpenId: (id: number | null) => void }) {
  const done = unit.skills.every((sk) => sk.state === "completed");
  const [book, setBook] = useState(false);
  const mascotLeft = unit.position % 2 === 1;
  return (
    <section className={s.unit} style={{ ["--u" as string]: unit.color }}>
      <header className={s.banner}>
        <div><small>Unit {unit.position}</small><h2>{unit.title}</h2></div>
        <button className={s.guide} onClick={() => setBook(true)}>📘 Guidebook</button>
      </header>
      {book && <Guidebook unitId={unit.id} onClose={() => setBook(false)} />}
      <div className={s.track}>
        <Mascot size={110} mood={done ? "cheer" : "happy"} className={s.mascot}
          style={{ [mascotLeft ? "left" : "right"]: "6%" }} />
        {unit.skills.map((skill, i) => (
          <SkillNode key={skill.id} skill={skill} index={i} color={unit.color} open={openId === skill.id}
            onToggle={() => setOpenId(openId === skill.id ? null : skill.id)} />
        ))}
        <div className={`${s.trophy} ${done ? s.done : ""}`} title={done ? "Unit complete!" : "Finish the unit to earn the trophy"}>
          <Trophy size={38} />
        </div>
      </div>
    </section>
  );
}

export default function LearningPath() {
  const { toast, me } = useApp();
  const [path, setPath] = useState<Path | null>(null);
  const [openId, setOpenId] = useState<number | null>(null);
  const root = useRef<HTMLDivElement>(null);

  // Refetch when the learner's XP changes (e.g. returning from a lesson).
  useEffect(() => { api.path().then(setPath).catch((e) => toast({ icon: "⚠️", title: e.message })); }, [toast, me?.xp_total, me?.course.id]);

  // Close the node popover on outside click.
  useEffect(() => {
    const close = (e: MouseEvent) => { if (!(e.target as Element).closest("[aria-expanded], [data-popover]")) setOpenId(null); };
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, []);

  const scrollToActive = () => root.current?.querySelector("[data-active]")?.scrollIntoView({ behavior: "smooth", block: "center" });
  useEffect(() => { if (path) setTimeout(scrollToActive, 50); }, [path]);

  if (!path) return <div style={{ display: "grid", placeItems: "center", height: "60vh" }}><Mascot mood="think" className="bounce" /></div>;
  return (
    <div ref={root}>
      {path.units.map((u) => <Unit key={u.id} unit={u} openId={openId} setOpenId={setOpenId} />)}
      <button className={s.jump} onClick={scrollToActive} aria-label="Jump to current lesson">
        <svg width="24" height="24" viewBox="0 0 24 24"><path d="M12 4v16M5 13l7 7 7-7" stroke="currentColor" strokeWidth="3" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
    </div>
  );
}
