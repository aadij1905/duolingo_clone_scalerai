"use client";
import { useEffect, useState } from "react";
import { Gem, Heart } from "@/components/Icons";
import { useApp } from "@/components/Providers";
import { api, ApiError, type Me, type ShopItems } from "@/lib/api";
import s from "../pages.module.css";

export default function ShopPage() {
  const { me, setMe, toast } = useApp();
  const [items, setItems] = useState<ShopItems | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.shop().then(setItems).catch(() => {}); }, []);
  if (!me || !items) return null;

  // Spend gems only after the server confirms (never predict a currency balance client-side).
  async function buy(action: () => Promise<Me>, success: string) {
    setBusy(true);
    try { setMe(await action()); toast({ icon: "🛍️", title: success }); }
    catch (e) { toast({ icon: "💎", title: (e as ApiError).message }); }
    finally { setBusy(false); }
  }

  const full = me.hearts >= me.max_hearts;
  return (
    <div className={s.page}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 className={s.title}>Shop</h1>
        <b style={{ display: "flex", alignItems: "center", gap: 6, color: "var(--macaw)", fontSize: 20 }}><Gem /> {me.gems}</b>
      </div>

      <section>
        <h2>Hearts</h2>
        <div className={s.row}>
          <span className={s.iconBox}><Heart size={52} /></span>
          <div className={s.grow}>
            <h3>Refill hearts</h3>
            <span className="muted">{full ? "You have full hearts" : `Get full hearts so you can worry less about making mistakes (${me.hearts}/${me.max_hearts})`}</span>
          </div>
          <button className="btn ghost" disabled={busy || full} onClick={() => buy(api.refillHearts, "Hearts refilled!")}>
            <Gem size={20} /> {items.heart_refill.cost}
          </button>
        </div>
        <div className={s.row}>
          <span className={s.iconBox}>💜</span>
          <div className={s.grow}><h3>Unlimited hearts</h3><span className="muted">Never run out of hearts with Super!</span></div>
          <span className="coming-soon">Coming soon</span>
        </div>
      </section>

      <section>
        <h2>Power-ups</h2>
        <div className={s.row}>
          <span className={s.iconBox}>🧊</span>
          <div className={s.grow}>
            <h3>Streak Freeze</h3>
            <span className="muted">Streak Freeze allows your streak to remain in place for one full day of inactivity.</span>
            <small style={{ color: "var(--macaw)" }}>{me.streak_freezes} / {items.streak_freeze.max} equipped</small>
          </div>
          <button className="btn ghost" disabled={busy || me.streak_freezes >= items.streak_freeze.max}
            onClick={() => buy(api.buyFreeze, "Streak Freeze equipped!")}>
            <Gem size={20} /> {items.streak_freeze.cost}
          </button>
        </div>
        <div className={s.row}>
          <span className={s.iconBox}>⏱️</span>
          <div className={s.grow}><h3>Double or Nothing</h3><span className="muted">Wager gems on keeping a 7 day streak.</span></div>
          <span className="coming-soon">Coming soon</span>
        </div>
      </section>

      <section className="card" style={{ background: "linear-gradient(135deg,#0a2b3d,#1d4a6b)", color: "#fff", border: 0 }}>
        <h2 style={{ color: "#fff" }}>Super Duolingo</h2>
        <p style={{ opacity: 0.85 }}>Unlimited hearts, no ads, personalized practice and more. In-app purchases are mocked in this clone.</p>
        <span className="coming-soon" style={{ marginTop: 12 }}>Coming soon</span>
      </section>
    </div>
  );
}
