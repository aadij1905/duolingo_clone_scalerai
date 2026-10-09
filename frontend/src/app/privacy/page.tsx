import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Privacy – Duolingo Clone" };

// Plain page linked from Google's OAuth consent screen (required to publish Google sign-in).
export default function PrivacyPage() {
  return (
    <main style={{ maxWidth: 680, margin: "0 auto", padding: "40px 16px", display: "grid", gap: 16, lineHeight: 1.6 }}>
      <h1>Privacy policy</h1>
      <p className="muted">Duolingo Clone is a student project (an SDE full-stack assignment). It is not affiliated with Duolingo.</p>
      <h2>What we store</h2>
      <ul style={{ paddingLeft: 20 }}>
        <li>Your learner profile: display name, username, timezone, chosen course and daily goal.</li>
        <li>Your progress: XP, streak, hearts, gems, completed lessons, answers you gave, quests and badges.</li>
        <li>If you create a password, only a salted scrypt hash of it, never the password itself.</li>
        <li>If you sign in with Google, your Google account ID, email address and name. We request no other Google data.</li>
        <li>A sign-in cookie identifying your session. The server keeps only a hash of it.</li>
      </ul>
      <h2>What we don&apos;t do</h2>
      <p>No ads, no tracking or analytics, and your data is never sold or shared. Speech recognition and audio run in your browser.</p>
      <h2>Deleting your data</h2>
      <p>Settings → Demo controls → Reset my progress erases your progress. To delete your account entirely, contact the developer through the project&apos;s GitHub page.</p>
      <p><Link href="/" style={{ color: "var(--macaw)" }}>← Back to learning</Link></p>
    </main>
  );
}
