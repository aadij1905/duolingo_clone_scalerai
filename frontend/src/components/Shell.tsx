"use client";
// Main app chrome shared by every non-lesson page.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, ApiError, type CourseProgress, type Leaderboard, type Quest } from "@/lib/api";
import { useApp } from "./Providers";
import { Chest, Dumbbell, Flame, Gem, Heart, Home, Lightning, More, Shield, Shop, UserIcon } from "./Icons";
import s from "./shell.module.css";

const NAV = [
  { href: "/", label: "Learn", Icon: Home },
  { href: "/practice", label: "Practice", Icon: () => <span style={{ color: "#1cb0f6", display: "flex" }}><Dumbbell size={28} /></span> },
  { href: "/leaderboard", label: "Leaderboards", Icon: () => <Shield size={28} /> },
  { href: "/quests", label: "Quests", Icon: Chest },
  { href: "/shop", label: "Shop", Icon: Shop },
  { href: "/profile", label: "Profile", Icon: UserIcon },
  { href: "/settings", label: "More", Icon: More },
];

function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), intervalMs); return () => clearInterval(t); }, [intervalMs]);
  return now;
}

/** Course flag, streak, gems and hearts, each opening a small popover. */
export function StatsBar() {
  const { me, setMe, refreshMe, toast } = useApp();
  const [open, setOpen] = useState<null | "course" | "streak" | "gems" | "hearts">(null);
  const [courses, setCourses] = useState<CourseProgress[] | null>(null);
  const bar = useRef<HTMLDivElement>(null);
  const now = useNow();
  // Close on click outside or Escape (not on mouse-leave: the gap above the popover would close it mid-reach).
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => { if (!bar.current?.contains(e.target as Node)) setOpen(null); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(null); };
    document.addEventListener("click", onClick);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("click", onClick); document.removeEventListener("keydown", onKey); };
  }, [open]);
  useEffect(() => { if (open === "course") api.courses().then(setCourses).catch(() => {}); }, [open]);

  // A heart regenerates while the learner watches: refetch when the timer hits zero.
  const nextHeart = me?.next_heart_at ? new Date(me.next_heart_at).getTime() - now : null;
  useEffect(() => { if (nextHeart !== null && nextHeart <= 0) void refreshMe(); }, [nextHeart, refreshMe]);

  if (!me) return <div className={s.stats} style={{ height: 44 }} />;
  const toggle = (k: typeof open) => setOpen(open === k ? null : k);
  const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.floor((ms % 60000) / 1000)).padStart(2, "0")}`;

  async function switchCourse(id: number) {
    try { setMe(await api.updateMe({ course_id: id })); setOpen(null); }
    catch (e) { toast({ icon: "⚠️", title: (e as ApiError).message }); }
  }

  async function refill() {
    try { setMe(await api.refillHearts()); toast({ icon: "❤️", title: "Hearts refilled!" }); setOpen(null); }
    catch (e) { toast({ icon: "💎", title: (e as ApiError).message }); }
  }

  return (
    <div className={s.stats} ref={bar}>
      <button className={`${s.stat} ${s.flag}`} onClick={() => toggle("course")} aria-label={`Learning ${me.course.title}. Switch course`}>
        {me.course.flag}
      </button>
      <button className={s.stat} onClick={() => toggle("streak")} aria-label={`${me.streak} day streak`}
        style={{ color: me.streak_extended_today ? "var(--fox)" : "var(--faint)" }}>
        <Flame muted={!me.streak_extended_today} /> {me.streak}
      </button>
      <button className={s.stat} onClick={() => toggle("gems")} style={{ color: "var(--macaw)" }} aria-label={`${me.gems} gems`}>
        <Gem /> {me.gems}
      </button>
      <button className={s.stat} onClick={() => toggle("hearts")} style={{ color: "var(--cardinal)" }} aria-label={`${me.hearts} hearts`}>
        <Heart /> {me.hearts}
      </button>

      {open === "course" && (
        <div className={s.popover}>
          <h3>My courses</h3>
          {(courses ?? []).map((c) => (
            <button key={c.id} className={`${s.courseRow} ${c.current ? s.currentCourse : ""}`} onClick={() => switchCourse(c.id)}>
              <span className={s.flag}>{c.flag}</span>
              <span style={{ flex: 1, textAlign: "left" }}><b>{c.title}</b><small className="muted"> · {c.skills_done}/{c.skills_total} skills</small></span>
              {c.current && <span aria-label="current">✓</span>}
            </button>
          ))}
          {!courses && <p className="muted">Loading…</p>}
        </div>
      )}
      {open === "streak" && (
        <div className={s.popover}>
          <h3><Flame /> {me.streak} day streak</h3>
          <p className="muted">{me.streak_extended_today ? "You've extended your streak today. See you tomorrow!" : "Do a lesson today to extend your streak!"}</p>
          <p>🧊 Streak Freezes equipped: <b>{me.streak_freezes}</b> / 2</p>
          <p className="muted">Longest streak: {me.longest_streak} days</p>
        </div>
      )}
      {open === "gems" && (
        <div className={s.popover}>
          <h3>Gems</h3>
          <p className="muted">You have {me.gems} gems. Spend them in the shop on refills and Streak Freezes.</p>
          <Link href="/shop" className="btn ghost">Go to shop</Link>
        </div>
      )}
      {open === "hearts" && (
        <div className={s.popover}>
          <h3>Hearts</h3>
          <div className={s.heartRow}>{Array.from({ length: me.max_hearts }, (_, i) => <Heart key={i} size={32} muted={i >= me.hearts} />)}</div>
          <p className="muted">
            {me.hearts >= me.max_hearts ? "You have full hearts. Keep on learning!" : `Next heart in ${mmss(Math.max(0, nextHeart ?? 0))}`}
          </p>
          <button className="btn ghost" onClick={refill} disabled={me.hearts >= me.max_hearts}>
            Refill hearts <Gem size={20} /> 350
          </button>
          <Link href="/practice" className="btn ghost">Practice to earn hearts</Link>
          <button className="btn ghost gray" disabled>Unlimited hearts <span className="coming-soon">Super · soon</span></button>
        </div>
      )}
    </div>
  );
}

function QuestsCard() {
  const { me } = useApp();
  const [quests, setQuests] = useState<Quest[] | null>(null);
  useEffect(() => { api.quests().then(setQuests).catch(() => {}); }, [me?.xp_total, me?.gems]);
  if (!quests) return null;
  return (
    <section className="card">
      <div className={s.cardHead}><h2>Daily Quests</h2><Link href="/quests">View all</Link></div>
      <div style={{ display: "grid", gap: 16 }}>
        {quests.map((q) => (
          <div key={q.code} className={s.questRow}>
            <Lightning size={30} />
            <div>
              <b>{q.title}</b>
              <div className="bar" style={{ ["--fill" as string]: "var(--bee)" }}><span style={{ width: `${(100 * q.progress) / q.target}%` }} /></div>
              <small className="muted">{q.progress} / {q.target}</small>
            </div>
            <Chest size={30} className={q.claimed ? s.openedChest : undefined} />
          </div>
        ))}
      </div>
    </section>
  );
}

function LeagueCard() {
  const { me } = useApp();
  const [board, setBoard] = useState<Leaderboard | null>(null);
  useEffect(() => { api.leaderboard().then(setBoard).catch(() => {}); }, [me?.xp_total]);
  const mine = board?.entries.find((e) => e.is_me);
  return (
    <section className="card">
      <div className={s.cardHead}><h2>{board?.league ?? me?.league ?? "Bronze"} League</h2><Link href="/leaderboard">View league</Link></div>
      <div className={s.questRow}>
        <Shield size={48} />
        <div>
          {mine ? <b>You&apos;re ranked #{mine.rank}</b> : <b>Loading…</b>}
          <small className="muted">{mine ? `${mine.xp} XP this week. ${mine.zone === "promotion" ? "You're in the promotion zone!" : mine.zone === "demotion" ? "Earn XP to avoid demotion!" : "Earn XP to reach the top 7!"}` : ""}</small>
        </div>
      </div>
    </section>
  );
}

export function RightRail() {
  return (
    <aside className={s.rail}>
      <StatsBar />
      <section className={`card ${s.superCard}`}>
        <span className="coming-soon">Super</span>
        <h2 style={{ marginTop: 8 }}>Try Super for free</h2>
        <p style={{ opacity: 0.85, marginBottom: 14 }}>No ads, unlimited hearts, and personalized practice.</p>
        <button className="btn block" disabled>Coming soon</button>
      </section>
      <LeagueCard />
      <QuestsCard />
      <nav className={s.footerLinks}><span>About</span><span>Blog</span><span>Store</span><span>Efficacy</span><span>Careers</span><span>Privacy</span></nav>
    </aside>
  );
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { me } = useApp();
  useEffect(() => { if (me && !me.onboarded) router.replace("/welcome"); }, [me, router]);
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));
  return (
    <div className={s.shell}>
      <nav className={s.sidebar} aria-label="Main">
        <Link href="/" className={s.logo}>duolingo</Link>
        {NAV.map(({ href, label, Icon }) => (
          <Link key={href} href={href} className={`${s.navItem} ${isActive(href) ? s.active : ""}`}>
            <Icon size={32} /> <span>{label}</span>
          </Link>
        ))}
      </nav>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className={s.topbar}><StatsBar /></div>
        <div className={s.main}>
          <main className={s.content}>{children}</main>
          <RightRail />
        </div>
      </div>
      <nav className={s.bottomnav} aria-label="Main mobile">
        {NAV.filter((n) => n.href !== "/practice").map(({ href, label, Icon }) => (
          <Link key={href} href={href} aria-label={label} className={isActive(href) ? s.active : ""}><Icon size={30} /></Link>
        ))}
      </nav>
    </div>
  );
}
