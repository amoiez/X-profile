import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "X Behavior Analyzer",
  description:
    "Analyze observable public posting patterns of any public X profile. " +
    "Reports observable behavior only — not personality, intent, or identity.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
