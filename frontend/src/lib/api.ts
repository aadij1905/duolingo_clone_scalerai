// Typed client for the FastAPI backend (proxied at /api by next.config.ts).

export type Course = { id: number; title: string; flag: string; language_code: string; tts_locale: string; word_spacing: boolean };
export type CourseProgress = Course & { skills_done: number; skills_total: number; current: boolean };

export type Me = {
  id: number; username: string; display_name: string; avatar_color: string; timezone: string;
  registered: boolean; has_password: boolean; google_email: string | null; onboarded: boolean; course: Course; league: string;
  league_event: { promoted?: string; demoted?: string; rank?: number };
  xp_total: number; gems: number; hearts: number; max_hearts: number; next_heart_at: string | null;
  streak: number; longest_streak: number; streak_extended_today: boolean; streak_freezes: number;
  max_streak_freezes: number; heart_refill_cost: number;
  streak_event: { freezes_used?: number; streak_lost?: number };
  daily_goal_xp: number; daily_xp: number; today: string;
};

export type SkillState = "locked" | "active" | "completed";
export type PathSkill = {
  id: number; title: string; icon: string; state: SkillState;
  lessons_completed: number; lessons_total: number; legendary: boolean;
};
export type PathUnit = { id: number; position: number; title: string; description: string; color: string; skills: PathSkill[] };
export type LearningPath = { course: Course; units: PathUnit[] };

export type Mode = "lesson" | "practice" | "legendary";
export type PracticeKind = "mix" | "listening" | "speaking" | "mistakes";
/** A target-language word with an optional translation hint. */
export type Token = { t: string; h?: string };
type Ex<T extends string, P> = { id: number; type: T; prompt: string; tts: string | null; reading?: string | null; payload: P };
export type Exercise =
  | Ex<"multiple_choice", { options: { text: string; emoji: string; reading?: string | null; say?: string | null }[]; new_word?: boolean }>
  | Ex<"translate", { tokens?: Token[]; reading?: string | null; sentence?: string; words: string[]; target?: boolean }>
  | Ex<"match_pairs", { pairs: [string, string][] }>
  | Ex<"fill_blank", { before: Token[]; after: Token[]; options: string[]; translation: string }>
  | Ex<"type_answer", { text: string; placeholder: string }>
  | Ex<"listen_tap", { words: string[] }>
  | Ex<"listen_type", { placeholder: string }>
  | Ex<"speak", { tokens: Token[]; reading?: string | null; translation?: string }>;
export type ExerciseType = Exercise["type"];
export const LISTENING: ExerciseType[] = ["listen_tap", "listen_type"];
export type AnswerValue = string | [string, string][];

export type LessonSession = {
  id: string; mode: Mode; skill_id: number; status: string; exercises: Exercise[]; hearts: number; no_heart_loss: boolean;
  deadline: string | null; time_limit_s: number | null; max_mistakes: number | null;
};
export type AnswerResult = {
  correct: boolean; typo: boolean; skipped: boolean; solution: string; hearts: number;
  meaning: string | null; reading: string | null; // English meaning and how to say it, shown after answering
  status: "active" | "failed" | "completed"; mistakes: number;
};
export type Badge = { code: string; title: string; description: string; icon: string; color: string; unlocked_at?: string | null };
export type LessonResult = {
  xp_earned: number; perfect: boolean; gems_earned: number; accuracy: number; duration_s: number;
  streak: number; streak_extended: boolean; daily_xp: number; daily_goal_xp: number; daily_goal_reached: boolean;
  hearts: number; achievements: Badge[]; mode: Mode;
};
export type LeaderboardEntry = { rank: number; user_id: number; name: string; avatar_color: string; xp: number; is_me: boolean; zone: "promotion" | "demotion" | null };
export type Leaderboard = { league: string; tier: number; ends_at: string; entries: LeaderboardEntry[] };
export type Profile = {
  user: Me; joined: string;
  stats: { xp_total: number; streak: number; longest_streak: number; lessons_done: number; skills_done: number; perfect_lessons: number; legendary_skills: number; goal_days: number };
  weekly_xp: { date: string; xp: number }[];
  practiced_days: string[];
  achievements: Badge[];
};
export type Quest = { code: string; title: string; progress: number; target: number; reward: number; claimed: boolean };
export type Phrase = { kind: "word" | "sentence"; text: string; translation: string; reading: string | null; emoji: string | null };
export type Guidebook = { title: string; description: string; position: number; skills: { title: string; icon: string; phrases: Phrase[] }[] };
export type ShopItems = { heart_refill: { cost: number }; streak_freeze: { cost: number; max: number } };

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

async function request<T>(path: string, init?: RequestInit, retried = false): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    // 409 "conflict" = optimistic-lock collision on the server; one retry is safe.
    if (res.status === 409 && body.error === "conflict" && !retried) return request<T>(path, init, true);
    const detail = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
    throw new ApiError(res.status, body.error ?? "error", body.message ?? detail ?? "Something went wrong");
  }
  return body as T;
}

const post = <T>(path: string, data?: unknown) => request<T>(path, { method: "POST", body: data ? JSON.stringify(data) : undefined });

export type MeUpdate = Partial<Pick<Me, "daily_goal_xp" | "display_name" | "timezone" | "onboarded">> & { course_id?: number };

export const api = {
  me: () => request<Me>("/me"),
  updateMe: (data: MeUpdate) => request<Me>("/me", { method: "PATCH", body: JSON.stringify(data) }),
  guest: () => post<{ ok: boolean }>("/auth/guest"),
  register: (username: string, password: string) => post<Me>("/auth/register", { username, password }),
  login: (username: string, password: string) => post<{ ok: boolean }>("/auth/login", { username, password }),
  logout: () => post<{ ok: boolean }>("/auth/logout"),
  demoLogin: () => post<{ ok: boolean }>("/dev/demo"),
  authConfig: () => request<{ google_client_id: string | null }>("/auth/config"),
  google: (credential: string) => post<{ ok: boolean }>("/auth/google", { credential }),
  courses: () => request<CourseProgress[]>("/courses"),
  guidebook: (unitId: number) => request<Guidebook>(`/units/${unitId}/guidebook`),
  quests: () => request<Quest[]>("/quests"),
  claimQuest: (code: string) => post<{ gems_earned: number; me: Me }>(`/quests/${code}/claim`),
  profile: () => request<Profile>("/me/profile"),
  path: () => request<LearningPath>("/path"),
  startSession: (skill_id: number | null, mode: Mode, kind: PracticeKind = "mix") =>
    post<LessonSession>("/sessions", { skill_id, mode, kind }),
  answer: (sessionId: string, exercise_id: number, value: AnswerValue, skip = false) =>
    post<AnswerResult>(`/sessions/${sessionId}/answers`, { exercise_id, value, skip }),
  complete: (sessionId: string) => post<LessonResult>(`/sessions/${sessionId}/complete`),
  leaderboard: () => request<Leaderboard>("/leaderboard"),
  shop: () => request<ShopItems>("/shop"),
  refillHearts: () => post<Me>("/shop/heart-refill"),
  buyFreeze: () => post<Me>("/shop/streak-freeze"),
  devClock: () => request<{ now: string; offset_days: number }>("/dev/clock"),
  timeTravel: (days: number) => post<{ now: string; offset_days: number }>("/dev/time-travel", { days }),
  resetDemo: () => post<{ ok: boolean }>("/dev/reset"),
};
