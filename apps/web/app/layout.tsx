import type { Metadata } from "next";
import { Syne, DM_Sans, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";
import { CommandPalette } from "@/components/command-palette";
import { cv } from "@content/cv";

const display = Syne({
  subsets: ["latin"],
  variable: "--font-display-loaded",
  display: "swap",
});

const sans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-sans-loaded",
  display: "swap",
});

const mono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-mono-loaded",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: `${cv.name} — Portfolio`,
    template: `%s · ${cv.name}`,
  },
  description: cv.summary,
  openGraph: {
    title: `${cv.name} — Portfolio`,
    description: cv.summary,
    type: "website",
    locale: "en_US",
  },
  metadataBase: new URL(cv.links.site),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${display.variable} ${sans.variable} ${mono.variable} antialiased`}
        style={{
          fontFamily: "var(--font-sans-loaded), var(--font-sans)",
        }}
      >
        <Providers>
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--color-accent)] focus:px-4 focus:py-2 focus:text-[#04110c]"
          >
            Skip to content
          </a>
          <SiteHeader />
          <main id="main">{children}</main>
          <SiteFooter />
          <CommandPalette />
        </Providers>
      </body>
    </html>
  );
}
