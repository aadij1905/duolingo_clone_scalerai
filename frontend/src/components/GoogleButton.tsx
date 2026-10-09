"use client";
// "Sign in with Google" via Google Identity Services. Renders nothing unless the
// backend has GOOGLE_CLIENT_ID set (it verifies the ID token server-side).
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useApp } from "./Providers";

type Gis = {
  initialize: (o: { client_id: string; callback: (r: { credential: string }) => void }) => void;
  renderButton: (el: HTMLElement, o: Record<string, string | number>) => void;
};
declare global { interface Window { google?: { accounts: { id: Gis } } } }

let script: Promise<void> | null = null;
const loadGis = () => script ??= new Promise((resolve, reject) => {
  const el = document.createElement("script");
  el.src = "https://accounts.google.com/gsi/client";
  el.async = true;
  el.onload = () => resolve();
  el.onerror = () => { script = null; reject(new Error("Couldn't load Google sign-in")); };
  document.head.appendChild(el);
});

export default function GoogleButton({ onDone }: { onDone: () => void | Promise<void> }) {
  const { refreshMe, toast } = useApp();
  const box = useRef<HTMLDivElement>(null);
  const [clientId, setClientId] = useState<string | null>(null);
  const done = useRef(onDone);
  useEffect(() => { done.current = onDone; });

  useEffect(() => { api.authConfig().then((c) => setClientId(c.google_client_id)).catch(() => {}); }, []);

  useEffect(() => {
    if (!clientId) return;
    loadGis().then(() => {
      const gis = window.google?.accounts.id;
      if (!gis || !box.current) return;
      gis.initialize({
        client_id: clientId,
        callback: async ({ credential }) => {
          try { await api.google(credential); await refreshMe(); await done.current(); }
          catch (e) { toast({ icon: "⚠️", title: (e as ApiError).message }); }
        },
      });
      gis.renderButton(box.current, { theme: "outline", size: "large", shape: "pill", text: "continue_with", width: 300 });
    }).catch((e: Error) => toast({ icon: "⚠️", title: e.message }));
  }, [clientId, refreshMe, toast]);

  return clientId ? <div ref={box} style={{ display: "flex", justifyContent: "center", minHeight: 44 }} /> : null;
}
