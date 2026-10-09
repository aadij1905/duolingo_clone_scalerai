"use client";
// App-wide client state: the current learner ("me") and toast notifications.
// Server-confirmed values only: we refetch `me` after every mutation instead
// of predicting XP/gems/hearts on the client (those are values users care about).
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, ApiError, type Me } from "@/lib/api";
import { setSpeechLocale } from "@/lib/sound";
import { Shield } from "./Icons";
import Mascot from "./Mascot";
import Modal, { Confetti } from "./Modal";

type Toast = { id: number; icon: string; title: string; body?: string };
type Ctx = {
  me: Me | null;
  setMe: (me: Me) => void;
  refreshMe: () => Promise<void>;
  toast: (t: Omit<Toast, "id">) => void;
};

const AppContext = createContext<Ctx | null>(null);

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside <Providers>");
  return ctx;
}

export default function Providers({ children }: { children: React.ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [league, setLeague] = useState<Me["league_event"] | null>(null);
  const nextId = useRef(0);

  const toast = useCallback((t: Omit<Toast, "id">) => {
    const id = ++nextId.current;
    setToasts((all) => [...all, { ...t, id }]);
    setTimeout(() => setToasts((all) => all.filter((x) => x.id !== id)), 3800);
  }, []);

  // The server reports a streak repair exactly once (the read that applied it), so announcing it here is safe on every refresh.
  const applyMe = useCallback((m: Me) => {
    setMe(m);
    setSpeechLocale(m.course.tts_locale);
    if (m.league_event.promoted || m.league_event.demoted) setLeague(m.league_event);
    if (m.streak_event.freezes_used) toast({ icon: "🧊", title: "Streak Freeze used", body: `Your ${m.streak} day streak was saved!` });
    if (m.streak_event.streak_lost) toast({ icon: "💔", title: `You lost your ${m.streak_event.streak_lost} day streak`, body: "Start a new one today!" });
  }, [toast]);

  // After sign-in / sign-out too: a browser without a session becomes a new guest.
  const refreshMe = useCallback(async () => {
    try { applyMe(await api.me()); } catch (e) {
      if ((e as ApiError).status === 401) { await api.guest(); return applyMe(await api.me()); }
      toast({ icon: "⚠️", title: "Can't reach the server", body: String((e as Error).message) });
    }
  }, [applyMe, toast]);

  // Every browser is a learner: the first visit creates a guest account (HttpOnly cookie).
  // One shared promise, so StrictMode's double-run effect can't create two guests.
  const boot = useRef<Promise<Me | null> | null>(null);
  const loadMe = useCallback(() => boot.current ??= api.me().catch(async (e: ApiError) => {
    if (e.status !== 401) return null;
    await api.guest();
    return api.me().catch(() => null);
  }), []);

  useEffect(() => {
    void (async () => {
      const current = await loadMe();
      if (!current) return refreshMe();
      // First visit from this browser: store the learner's timezone so streak days are local days.
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      applyMe(current);
      if (tz && tz !== current.timezone) setMe(await api.updateMe({ timezone: tz }).catch(() => current));
    })();
  }, [refreshMe, applyMe, loadMe]);

  const setMeTracked = useCallback((m: Me) => { setMe(m); setSpeechLocale(m.course.tts_locale); }, []);

  return (
    <AppContext.Provider value={{ me, setMe: setMeTracked, refreshMe, toast }}>
      {/* Pages only mount once the learner (or new guest) is loaded, so every API call is signed in. */}
      {me ? children : <div style={{ display: "grid", placeItems: "center", minHeight: "100dvh" }}><Mascot mood="think" className="bounce" /></div>}
      {league && (
        <Modal label="League result" onClose={() => setLeague(null)}>
          {league.promoted && <Confetti />}
          <span style={{ display: "grid", placeItems: "center" }}><Shield size={96} color={league.promoted ? "#ffc800" : "#cd7900"} /></span>
          <h2>{league.promoted ? `Promoted to the ${league.promoted} League!` : `You moved to the ${league.demoted} League`}</h2>
          <p className="muted">
            {league.promoted ? `You finished #${league.rank} last week. Great work!` : "Earn XP this week to climb back up."}
          </p>
          <button className="btn green block" onClick={() => setLeague(null)} autoFocus>Continue</button>
        </Modal>
      )}
      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="toast">
            <span className="icon">{t.icon}</span>
            <div><strong>{t.title}</strong>{t.body && <small>{t.body}</small>}</div>
          </div>
        ))}
      </div>
    </AppContext.Provider>
  );
}
