import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SentinelRAG — Self-Correcting RAG Platform",
  description:
    "A production-grade Self-Correcting Retrieval-Augmented Generation platform powered by DeepSeek V4.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
