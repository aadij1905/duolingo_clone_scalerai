"use client";
import { useState } from "react";
import { useApp } from "@/components/Providers";
import { api, ApiError } from "@/lib/api";
import s from "../pages.module.css";

/** Register (save this learner's progress with a password) or sign in to an existing account. */
export default function AccountForm({ mode, onDone }: { mode: "register" | "login"; onDone: () => void | Promise<void> }) {
  const { setMe, toast } = useApp();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      if (mode === "register") setMe(await api.register(username, password));
      else await api.login(username, password);
      await onDone();
    } catch (err) { toast({ icon: "⚠️", title: (err as ApiError).message }); }
    finally { setBusy(false); }
  }

  return (
    <form onSubmit={submit} className={s.form}>
      <label>Username
        <input className={s.input} value={username} onChange={(e) => setUsername(e.target.value)} required minLength={3} maxLength={20}
          pattern="[A-Za-z0-9_]+" autoComplete="username" autoCapitalize="off" />
      </label>
      <label>Password
        <input className={s.input} type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8}
          maxLength={128} autoComplete={mode === "register" ? "new-password" : "current-password"} />
      </label>
      <button className="btn block" disabled={busy}>{mode === "register" ? "Create account" : "Sign in"}</button>
    </form>
  );
}
