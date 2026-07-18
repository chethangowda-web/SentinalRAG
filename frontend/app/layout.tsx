import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/layout/providers";

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
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
