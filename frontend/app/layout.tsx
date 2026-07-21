import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/layout/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

export const metadata: Metadata = {
  title: {
    default: "SentinelRAG — Self-Correcting RAG Platform",
    template: "%s | SentinelRAG",
  },
  description:
    "A production-grade Self-Correcting Retrieval-Augmented Generation platform powered by DeepSeek V4 and LangGraph.",
  keywords: ["RAG", "AI", "retrieval augmented generation", "langgraph", "deepseek", "document search"],
  openGraph: {
    title: "SentinelRAG — Self-Correcting RAG Platform",
    description:
      "A production-grade Self-Correcting Retrieval-Augmented Generation platform powered by DeepSeek V4 and LangGraph.",
    type: "website",
    siteName: "SentinelRAG",
  },
  twitter: {
    card: "summary_large_image",
    title: "SentinelRAG — Self-Correcting RAG Platform",
    description:
      "A production-grade Self-Correcting Retrieval-Augmented Generation platform powered by DeepSeek V4 and LangGraph.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
