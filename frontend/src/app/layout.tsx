import type { Metadata, Viewport } from "next";
import { Nunito } from "next/font/google";
import Providers from "@/components/Providers";
import "./globals.css";

// Nunito is the closest freely-licensed match to Duolingo's rounded "Feather" typeface.
const nunito = Nunito({ variable: "--font-nunito", subsets: ["latin", "latin-ext"], weight: ["400", "600", "700", "800", "900"] });

export const metadata: Metadata = {
  title: "Duolingo Clone – Learn Spanish, French, Japanese or Hindi",
  description: "A Duolingo-style language learning app: learning path, lessons, streaks, XP, hearts and leagues.",
};

export const viewport: Viewport = { themeColor: "#58cc02" };

// Applies the saved theme before first paint so dark mode never flashes white.
const themeScript = `try{var t=localStorage.getItem("duo:theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={nunito.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
