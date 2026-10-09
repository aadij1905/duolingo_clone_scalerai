// Inline SVG icon set (original artwork, Duolingo-inspired colors).
// Stateless and size-driven, so one file serves the whole app.
type P = { size?: number; className?: string; muted?: boolean };

export const Flame = ({ size = 24, muted, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M12 2c1 3.5 5.5 6 5.5 11.2A5.6 5.6 0 0 1 12 19a5.6 5.6 0 0 1-5.5-5.8C6.5 10 8.6 9 9 6.5c1.6 1.3 2 2.8 2 4 1.8-1.4 1.5-5.5 1-8.5Z"
      fill={muted ? "var(--faint)" : "#ff9600"} transform="translate(0 2)" />
    <path d="M12 21c-2 0-3.3-1.4-3.3-3.2 0-2.2 2.2-3 2.6-4.9 1.4 1 4 2.6 4 4.9 0 1.8-1.3 3.2-3.3 3.2Z"
      fill={muted ? "var(--border)" : "#ffc800"} />
  </svg>
);

export const Gem = ({ size = 24, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M6 3h12l4 6-10 13L2 9l4-6Z" fill="#1cb0f6" />
    <path d="M2 9h20L12 22 2 9Z" fill="#1899d6" />
    <path d="M7.5 9 12 3l4.5 6L12 22 7.5 9Z" fill="#49c0f8" />
    <path d="M6 3h3L7.5 9H2l4-6Z" fill="#84d8ff" />
  </svg>
);

export const Heart = ({ size = 24, muted, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M12 21s-8.5-5.2-9.7-10.6C1.5 6.6 4 3.5 7.2 3.5c2 0 3.6 1 4.8 2.7 1.2-1.7 2.8-2.7 4.8-2.7 3.2 0 5.7 3.1 4.9 6.9C20.5 15.8 12 21 12 21Z"
      fill={muted ? "var(--faint)" : "#ff4b4b"} />
    <ellipse cx="7.5" cy="8" rx="2" ry="1.3" fill="#fff" opacity=".45" transform="rotate(-30 7.5 8)" />
  </svg>
);

export const Star = ({ size = 32, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="m12 2.5 2.9 6 6.6.8-4.9 4.5 1.3 6.5L12 17l-5.9 3.3 1.3-6.5L2.5 9.3l6.6-.8 2.9-6Z" fill="currentColor" />
  </svg>
);

export const Check = ({ size = 32, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="m4 12.5 5 5L20 6.5" fill="none" stroke="currentColor" strokeWidth="3.6" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export const Lock = ({ size = 28, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <rect x="4" y="10" width="16" height="12" rx="3" fill="currentColor" />
    <path d="M8 10V7a4 4 0 0 1 8 0v3" fill="none" stroke="currentColor" strokeWidth="2.6" />
  </svg>
);

export const Crown = ({ size = 24, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M3 8l4.5 4L12 5l4.5 7L21 8l-2 11H5L3 8Z" fill="#ffc800" stroke="#e5b400" strokeWidth="1.2" strokeLinejoin="round" />
  </svg>
);

export const Trophy = ({ size = 32, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M7 3h10v6a5 5 0 0 1-10 0V3Z" fill="currentColor" />
    <path d="M7 5H4a3 3 0 0 0 3 4M17 5h3a3 3 0 0 1-3 4" fill="none" stroke="currentColor" strokeWidth="2" />
    <path d="M10 14h4v4h-4zM7 18h10v3H7z" fill="currentColor" />
  </svg>
);

export const Speaker = ({ size = 24, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M3 9h4l5-4v14l-5-4H3V9Z" fill="currentColor" />
    <path d="M15.5 8.5a5 5 0 0 1 0 7M18 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
  </svg>
);

export const Close = ({ size = 24, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M5 5l14 14M19 5 5 19" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
  </svg>
);

export const Shield = ({ size = 32, color = "#cd7900", className }: P & { color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M12 2 3.5 5v6.5C3.5 17 7.3 20.7 12 22c4.7-1.3 8.5-5 8.5-10.5V5L12 2Z" fill={color} />
    <path d="M12 4.5 6 6.7v4.8c0 3.9 2.6 6.6 6 7.8V4.5Z" fill="#fff" opacity=".25" />
  </svg>
);

export const Dumbbell = ({ size = 28, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M2 10h2V8h3v8H4v-2H2v-4Zm20 0h-2V8h-3v8h3v-2h2v-4ZM7 11h10v2H7z" fill="currentColor" />
  </svg>
);

export const Chest = ({ size = 28, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M3 10a5 5 0 0 1 5-5h8a5 5 0 0 1 5 5v1H3v-1Z" fill="#ffc800" />
    <rect x="3" y="11" width="18" height="9" rx="2" fill="#ff9600" />
    <rect x="10" y="9" width="4" height="5" rx="1" fill="#fff" />
  </svg>
);

export const Shop = ({ size = 28, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M4 8h16l-1.3 12.2a2 2 0 0 1-2 1.8H7.3a2 2 0 0 1-2-1.8L4 8Z" fill="#ff4b4b" />
    <path d="M8.5 10V6.5a3.5 3.5 0 0 1 7 0V10" fill="none" stroke="#ea2b2b" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

export const Home = ({ size = 28, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M3 11 12 3l9 8v9a2 2 0 0 1-2 2h-4v-6H9v6H5a2 2 0 0 1-2-2v-9Z" fill="#ff9600" />
    <path d="M9 16h6v6H9z" fill="#ffc800" />
  </svg>
);

export const UserIcon = ({ size = 28, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <circle cx="12" cy="8" r="4.5" fill="#ce82ff" />
    <path d="M3.5 21a8.5 8.5 0 0 1 17 0H3.5Z" fill="#a568cc" />
  </svg>
);

export const More = ({ size = 28, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <circle cx="5" cy="12" r="2.4" fill="#1cb0f6" /><circle cx="12" cy="12" r="2.4" fill="#1cb0f6" /><circle cx="19" cy="12" r="2.4" fill="#1cb0f6" />
  </svg>
);

export const Lightning = ({ size = 24, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z" fill="#ffc800" stroke="#e5b400" strokeWidth="1" strokeLinejoin="round" />
  </svg>
);

export const Clock = ({ size = 24, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <circle cx="12" cy="12" r="9" fill="#1cb0f6" />
    <path d="M12 7v5l3 2" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" fill="none" />
  </svg>
);

export const Target = ({ size = 24, className }: P) => (
  <svg width={size} height={size} viewBox="0 0 24 24" className={className} aria-hidden>
    <circle cx="12" cy="12" r="9.5" fill="#58cc02" /><circle cx="12" cy="12" r="6" fill="#fff" /><circle cx="12" cy="12" r="2.8" fill="#58cc02" />
  </svg>
);
