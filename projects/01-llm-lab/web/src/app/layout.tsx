import type { Metadata } from 'next';
import { Syne, DM_Sans, IBM_Plex_Mono } from 'next/font/google';
import './globals.css';

const syne = Syne({
  subsets: ['latin'],
  variable: '--font-syne',
  display: 'swap',
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-dm-sans',
  display: 'swap',
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-ibm-plex-mono',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'LLM Lab - Foundation Ladder Demo',
  description: 'Interactive demonstration of LLM foundation concepts across 12 progressive levels',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${syne.variable} ${dmSans.variable} ${ibmPlexMono.variable} antialiased`} suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}