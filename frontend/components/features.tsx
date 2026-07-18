"use client";

import {
  Brain,
  FileText,
  Search,
  RefreshCw,
  Database,
  Zap,
} from "lucide-react";

const features = [
  {
    icon: FileText,
    title: "OCR Processing",
    description:
      "Extract text from scanned documents and images with high-accuracy OCR pipelines.",
  },
  {
    icon: Search,
    title: "Hybrid Retrieval",
    description:
      "Combine dense vector embeddings with sparse keyword search for optimal recall.",
  },
  {
    icon: Brain,
    title: "DeepSeek V4",
    description:
      "Powered by DeepSeek V4 for state-of-the-art language understanding and generation.",
  },
  {
    icon: RefreshCw,
    title: "Self-Correction",
    description:
      "Automatic detection and correction of hallucinations and inaccurate responses.",
  },
  {
    icon: Database,
    title: "Qdrant + PostgreSQL",
    description:
      "Vector search with Qdrant and relational storage with PostgreSQL working in tandem.",
  },
  {
    icon: Zap,
    title: "Real-Time Cache",
    description:
      "Redis-powered caching layer for sub-millisecond response times on repeated queries.",
  },
];

export function Features() {
  return (
    <section id="features" className="border-t border-border/50 py-24">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Built for Production
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Every component is chosen for scalability, reliability, and
            performance.
          </p>
        </div>

        <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div
                key={feature.title}
                className="group rounded-xl border border-border bg-card p-6 transition-colors hover:border-primary/50"
              >
                <div className="mb-4 inline-flex rounded-lg bg-primary/10 p-3 text-primary">
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="mb-2 text-lg font-semibold">{feature.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  {feature.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
