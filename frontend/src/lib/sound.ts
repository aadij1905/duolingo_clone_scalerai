// Sound effects synthesised with Web Audio (no audio assets to ship) and
// pronunciation via the browser's built-in speech synthesis.

const PREF_KEY = "duo:sound";

export function soundEnabled(): boolean {
  try { return localStorage.getItem(PREF_KEY) !== "off"; } catch { return true; }
}

export function setSoundEnabled(on: boolean) {
  try { localStorage.setItem(PREF_KEY, on ? "on" : "off"); } catch { /* storage blocked: keep default */ }
}

let ctx: AudioContext | null = null;

function tones(notes: [freq: number, start: number, dur: number][], type: OscillatorType = "sine", gain = 0.18) {
  if (typeof window === "undefined" || !soundEnabled()) return;
  ctx ??= new AudioContext();
  const t0 = ctx.currentTime;
  for (const [freq, start, dur] of notes) {
    const osc = ctx.createOscillator();
    const g = ctx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    g.gain.setValueAtTime(gain, t0 + start);
    g.gain.exponentialRampToValueAtTime(0.001, t0 + start + dur);
    osc.connect(g).connect(ctx.destination);
    osc.start(t0 + start);
    osc.stop(t0 + start + dur);
  }
}

export const sfx = {
  correct: () => tones([[880, 0, 0.12], [1318, 0.09, 0.22]], "triangle"),
  wrong: () => tones([[220, 0, 0.18], [185, 0.12, 0.25]], "square", 0.08),
  tap: () => tones([[600, 0, 0.05]], "sine", 0.06),
  complete: () => tones([[523, 0, 0.15], [659, 0.12, 0.15], [784, 0.24, 0.15], [1046, 0.36, 0.4]], "triangle"),
};

// The current course's speech locale (es-ES, fr-FR, ja-JP), set by <Providers> from /api/me.
let locale = "es-ES";
export function setSpeechLocale(l: string) { locale = l; }

const RATE_KEY = "duo:rate";
export const RATES = [0.75, 1, 1.25] as const;
export function playbackRate(): number {
  try { return Number(localStorage.getItem(RATE_KEY)) || 1; } catch { return 1; }
}
export function setPlaybackRate(r: number) {
  try { localStorage.setItem(RATE_KEY, String(r)); } catch { /* storage blocked: keep default */ }
}

// macOS "Eloquence" and novelty voices exist for every language and sound robotic.
const ROBOTIC = /\b(Eddy|Flo|Grandma|Grandpa|Reed|Rocko|Sandy|Shelley|Albert|Bad News|Bahh|Bells|Boing|Bubbles|Cellos|Jester|Organ|Superstar|Trinoids|Whisper|Wobble|Zarvox)\b/i;

/** The clearest installed voice for a language: Chrome's online Google voices, then macOS
 *  Premium / Enhanced downloads, then any regular voice; robotic ones only as a last resort. */
function voiceFor(lang: string, localOnly = false) {
  const norm = (l: string) => l.replace("_", "-").toLowerCase();
  const score = (v: SpeechSynthesisVoice) =>
    (/google/i.test(v.name) ? 8 : 0) + (/premium/i.test(v.name) ? 6 : 0) + (/enhanced|neural|natural/i.test(v.name) ? 4 : 0)
    + (norm(v.lang) === norm(lang) ? 2 : 0) - (ROBOTIC.test(v.name) ? 20 : 0);
  return window.speechSynthesis.getVoices()
    .filter((v) => norm(v.lang).startsWith(lang.slice(0, 2).toLowerCase()) && (!localOnly || v.localService))
    .sort((a, b) => score(b) - score(a))[0];
}

/** False when the OS has no voice for the course language (voices load async; null = unknown yet). */
export function hasVoice(lang = locale): boolean | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return false;
  if (window.speechSynthesis.getVoices().length === 0) return null;
  return Boolean(voiceFor(lang));
}

/** Name of the voice the course audio uses (voices load async: null until they do). */
export function voiceName(): string | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return null;
  return voiceFor(locale)?.name ?? null;
}

/** Speak target-language text in the course's language. `slow` is the turtle button. */
export function speak(text: string, slow = false) {
  if (typeof window === "undefined" || !("speechSynthesis" in window) || !soundEnabled()) return;
  window.speechSynthesis.cancel();
  // Chrome's online Google voices ignore `rate`, so slow mode uses an installed voice (which honours it)
  // and, for spaced languages, says each word as its own utterance so there's a clear pause between words.
  const voice = (slow && voiceFor(locale, true)) || voiceFor(locale);
  const parts = slow && text.trim().includes(" ") ? text.trim().split(/\s+/) : [text];
  for (const part of parts) {
    const u = new SpeechSynthesisUtterance(part);
    u.lang = locale;
    u.rate = playbackRate() * (slow ? 0.5 : 0.9); // normal is a touch slower than native: clearer for learners
    if (voice) u.voice = voice;
    window.speechSynthesis.speak(u); // utterances queue, so the words play one after another
  }
}

// ---- speech recognition (Chrome, Edge, Safari; not Firefox)
type Recognition = {
  lang: string; interimResults: boolean; maxAlternatives: number;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null; onend: (() => void) | null;
  start: () => void; stop: () => void;
};
function recognitionCtor(): (new () => Recognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as Record<string, new () => Recognition>;
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}
export const canRecognizeSpeech = () => recognitionCtor() !== null;

/** Listen once and resolve with the transcript ("" if nothing was heard). Call .stop() to end early. */
export function recognize(): { result: Promise<string>; stop: () => void } {
  const Ctor = recognitionCtor();
  if (!Ctor) return { result: Promise.reject(new Error("unsupported")), stop: () => {} };
  const rec = new Ctor();
  rec.lang = locale;
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  const result = new Promise<string>((resolve, reject) => {
    let text = "";
    rec.onresult = (e) => { text = Array.from(e.results).map((r) => r[0].transcript).join(" "); };
    rec.onerror = (e) => (e.error === "no-speech" ? resolve("") : reject(new Error(e.error)));
    rec.onend = () => resolve(text);
  });
  rec.start();
  return { result, stop: () => rec.stop() };
}
