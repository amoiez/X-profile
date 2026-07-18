import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "X Behavior Analyzer",
  description:
    "Analyze observable public posting patterns of any public X profile. " +
    "Reports observable behavior only — not personality, intent, or identity.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <div className="min-h-screen flex flex-col">
            <header className="border-b border-base-700 bg-base-800/60 backdrop-blur sticky top-0 z-10">
              <nav className="mx-auto max-w-6xl px-6 py-3 flex items-center justify-between">
                <Link href="/" className="font-semibold tracking-tight">
                  X Behavior Analyzer
                </Link>
                <div className="flex gap-4 text-sm text-gray-300">
                  <Link href="/" className="hover:text-accent">
                    Analyze
                  </Link>
                  <Link href="/history" className="hover:text-accent">
                    History
                  </Link>
                </div>
              </nav>
            </header>
            <main className="flex-1 mx-auto w-full max-w-6xl px-6 py-8">{children}</main>
            <footer className="border-t border-base-700 px-6 py-4 text-center text-xs text-gray-500">
              Analyzes public data only · reports observable posting patterns, not
              personality or intent.
            </footer>
          </div>
        </Providers>
      </body>
    </html>
  );
}
