// "Lingo", the app's original owl mascot, drawn from primitives so it scales
// anywhere and can change mood without extra assets.
type Mood = "happy" | "cheer" | "sad" | "think";

export default function Mascot({ size = 120, mood = "happy", className, style }: { size?: number; mood?: Mood; className?: string; style?: React.CSSProperties }) {
  const wingUp = mood === "cheer";
  const pupilY = mood === "sad" ? 57 : mood === "think" ? 49 : 53;
  const pupilDx = mood === "think" ? 4 : 0;
  return (
    <svg width={size} height={size * 1.08} viewBox="0 0 120 130" className={className} style={style} role="img" aria-label="Lingo the owl">
      {/* wings */}
      <ellipse cx="18" cy={wingUp ? 52 : 80} rx="12" ry="24" fill="#58a700" transform={wingUp ? "rotate(-35 18 52)" : "rotate(12 18 80)"} />
      <ellipse cx="102" cy={wingUp ? 52 : 80} rx="12" ry="24" fill="#58a700" transform={wingUp ? "rotate(35 102 52)" : "rotate(-12 102 80)"} />
      {/* body with ear tufts */}
      <path d="M22 40 C20 22 26 10 34 6 L44 20 C54 17 66 17 76 20 L86 6 C94 10 100 22 98 40 C106 62 104 100 86 114 C72 124 48 124 34 114 C16 100 14 62 22 40 Z" fill="#58cc02" />
      <ellipse cx="60" cy="92" rx="28" ry="24" fill="#89e219" />
      {/* eyes */}
      <circle cx="42" cy="52" r="17" fill="#fff" />
      <circle cx="78" cy="52" r="17" fill="#fff" />
      <circle cx={45 + pupilDx} cy={pupilY} r="8.5" fill="#4b4b4b" />
      <circle cx={75 + pupilDx} cy={pupilY} r="8.5" fill="#4b4b4b" />
      <circle cx={48 + pupilDx} cy={pupilY - 3} r="2.6" fill="#fff" />
      <circle cx={78 + pupilDx} cy={pupilY - 3} r="2.6" fill="#fff" />
      {mood === "sad" && (
        <>
          <path d="M28 36 L50 42" stroke="#3e8a00" strokeWidth="5" strokeLinecap="round" />
          <path d="M92 36 L70 42" stroke="#3e8a00" strokeWidth="5" strokeLinecap="round" />
        </>
      )}
      {/* beak */}
      <path d="M53 66 Q60 60 67 66 Q63 78 60 79 Q57 78 53 66 Z" fill="#ff9600" />
      <path d="M53 66 Q60 60 67 66 Q60 70 53 66 Z" fill="#ffc800" />
      {/* feet */}
      <path d="M44 118 l-6 8 h14 Z M76 118 l-6 8 h14 Z" fill="#ff9600" />
    </svg>
  );
}
