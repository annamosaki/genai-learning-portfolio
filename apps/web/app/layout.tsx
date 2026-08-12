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
  applicationName: cv.name,
  authors: [{ name: cv.name, url: cv.links.site }],
  creator: cv.name,
  keywords: [
    "Anna Mosaki",
    "quantitative researcher",
    "data scientist",
    "AI engineer",
    "portfolio",
    "ENSAE",
    "BNP Paribas",
  ],
  alternates: {
    canonical: "/",
  },
  openGraph: {
    title: `${cv.name} — Portfolio`,
    description: cv.summary,
    type: "website",
    locale: "en_US",
    url: cv.links.site,
    siteName: cv.name,
  },
  twitter: {
    card: "summary_large_image",
    title: `${cv.name} — Portfolio`,
    description: cv.summary,
  },
  robots: {
    index: true,
    follow: true,
  },
  metadataBase: new URL(cv.links.site),
};

const personJsonLd = {
  "@context": "https://schema.org",
  "@type": "Person",
  name: cv.name,
  url: cv.links.site,
  image: `${cv.links.site}/opengraph-image`,
  jobTitle: cv.title,
  email: cv.email,
  address: {
    "@type": "PostalAddress",
    addressLocality: "Lisbon",
    addressCountry: "PT",
  },
  sameAs: [cv.links.github, cv.links.linkedin],
  description: cv.summary,
};

const themeInitScript = `(function(){try{var k='anna-theme';var s=localStorage.getItem(k);var t=(s==='light'||s==='dark')?s:(window.matchMedia('(prefers-color-scheme: light)').matches?'light':'dark');document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','dark');}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning data-theme="dark">
      <body
        className={`${display.variable} ${sans.variable} ${mono.variable} antialiased`}
        style={{
          fontFamily: "var(--font-sans-loaded), var(--font-sans)",
        }}
      >
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(personJsonLd) }}
        />
        <Providers>
          <a
            href="#main"
            className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-[var(--color-accent)] focus:px-4 focus:py-2 focus:text-[var(--theme-accent-ink)]"
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
