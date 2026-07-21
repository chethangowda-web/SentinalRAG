"use client";

import { motion } from "framer-motion";
import {
  Brain,
  Shield,
  Search,
  FileText,
  GitBranch,
  BarChart3,
} from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "Self-Correcting Pipeline",
    description:
      "An 8-node LangGraph workflow that evaluates confidence after every retrieval. Low-confidence results trigger automatic query rewriting and re-retrieval.",
  },
  {
    icon: Search,
    title: "Hybrid Retrieval",
    description:
      "Combines vector similarity search (Qdrant, 384d) with PostgreSQL full-text search (BM25) using Reciprocal Rank Fusion and cross-encoder reranking.",
  },
  {
    icon: Shield,
    title: "Confidence Scoring",
    description:
      "Three-tier confidence system combining vector similarity (30%), reranker (50%), and coverage (20%). Maps to HIGH/MEDIUM/LOW tiers driving self-correction.",
  },
  {
    icon: GitBranch,
    title: "Contradiction Detection",
    description:
      "Identifies numerical and policy conflicts across retrieved chunks, preventing inconsistent answers by detecting conflicts before generation.",
  },
  {
    icon: FileText,
    title: "Multi-Format Support",
    description:
      "Ingest PDF, PNG, and JPEG documents up to 50MB. Automatic OCR via Tesseract for scanned documents, semantic chunking, and section header detection.",
  },
  {
    icon: BarChart3,
    title: "Full Observability",
    description:
      "Every query is traced through the pipeline with per-node latencies, confidence breakdowns, token usage, and exportable reports in JSON, CSV, or Markdown.",
  },
];

export function Features() {
  return (
    <section id="features" className="border-t py-20 sm:py-32">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Enterprise-Grade RAG
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Everything you need to build production-ready RAG applications with
            automatic hallucination prevention.
          </p>
        </div>

        <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              viewport={{ once: true }}
              className="group rounded-xl border bg-card p-6 transition-all duration-200 hover:shadow-md hover:border-primary/20"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10 text-primary mb-4 transition-colors group-hover:bg-primary/20">
                <feature.icon className="h-6 w-6" />
              </div>
              <h3 className="font-semibold mb-2">{feature.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
