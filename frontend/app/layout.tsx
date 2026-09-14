import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AIRB — Evidence-Calibrated Multi-Agent Decision Fusion",
  description:
    "Startup feasibility evaluator using calibrated multi-agent LLM decision fusion. Every score is traceable to cited historical evidence.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>{children}</body>
    </html>
  );
}
