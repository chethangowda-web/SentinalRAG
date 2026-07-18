"use client";

import { ArrowRight, Shield } from "lucide-react";

export function Hero() {
  return (
    <section className="relative flex min-h-screen items-center justify-center overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_hsl(var(--primary)/0.15)_0%,_transparent_70%)]" />

      <div className="relative z-10 mx-auto max-w-4xl px-4 text-center sm:px-6 lg:px-8">
        <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-secondary px-4 py-1.5 text-sm text-muted-foreground">
          <Shield className="h-4 w-4 text-primary" />
          Production-Grade RAG Platform
        </div>

        <h1 className="text-4xl font-bold tracking-tight sm:text-6xl lg:text-7xl">
          Self-Correcting
          <br />
          <span className="text-primary">Retrieval-Augmented</span>
          <br />
          Generation
        </h1>

        <p className="mt-6 text-lg leading-relaxed text-muted-foreground sm:text-xl">
          SentinelRAG combines DeepSeek V4, hybrid search, and an intelligent
          self-correction engine to deliver accurate, reliable answers from your
          documents.
        </p>

        <div className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <a
            href="#"
            className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-base font-medium text-primary-foreground transition-opacity hover:opacity-90"
          >
            View Documentation
            <ArrowRight className="h-4 w-4" />
          </a>
          <a
            href="#"
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-secondary px-6 py-3 text-base font-medium transition-colors hover:bg-muted"
          >
            Star on GitHub
          </a>
        </div>
      </div>
    </section>
  );
}
