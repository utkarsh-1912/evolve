import { IBM_Plex_Sans_Arabic, Instrument_Sans, JetBrains_Mono, Lexend } from "next/font/google";

// Free fonts only (docs/03 §4): Lexend display, Instrument Sans UI, JetBrains Mono meta, IBM Plex Sans Arabic.
export const lexend = Lexend({ subsets: ["latin"], variable: "--font-lexend", display: "swap" });
export const instrument = Instrument_Sans({ subsets: ["latin"], variable: "--font-instrument", display: "swap" });
export const jetbrains = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jetbrains", display: "swap" });
export const plexArabic = IBM_Plex_Sans_Arabic({
  subsets: ["arabic"],
  weight: ["400", "600", "700"],
  variable: "--font-plex-arabic",
  display: "swap",
});
