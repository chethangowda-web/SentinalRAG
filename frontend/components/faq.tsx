"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const faqs = [
  {
    q: "What makes SentinelRAG different from standard RAG?",
    a: "Standard RAG pipelines blindly generate answers from retrieved context. SentinelRAG continuously evaluates confidence, detects contradictions, and rewrites queries when results are uncertain — eliminating hallucinations before they happen.",
  },
  {
    q: "What LLM providers are supported?",
    a: "SentinelRAG supports any OpenAI-compatible API. DeepSeek, Groq, Featherless AI, and OpenAI are all supported out of the box. The backend is provider-agnostic through a configurable API key and base URL.",
  },
  {
    q: "How does the confidence scoring work?",
    a: "The composite score combines three weighted factors: vector similarity (30%), cross-encoder reranker score (50%), and result coverage (20%). Scores above 80 are HIGH, above 50 are MEDIUM, and below 50 trigger automatic query rewriting.",
  },
  {
    q: "What file formats are supported?",
    a: "PDF, PNG, and JPEG files up to 50MB. Digital PDFs are processed with PyMuPDF. Scanned documents and images use Tesseract OCR automatically. Text is chunked into 500-word segments with 100-word overlap.",
  },
  {
    q: "Can I run this locally?",
    a: "Yes. The recommended setup is Docker Compose, which starts all 5 services (PostgreSQL, Qdrant, FastAPI, Next.js, NGINX) with a single command. A local development setup without Docker is also supported.",
  },
  {
    q: "Is there an evaluation framework?",
    a: "Yes. A built-in benchmark suite with 18 questions across 7 categories measures faithfulness, hallucination rate, answer relevancy, context precision, context recall, and correctness. Results are compared against a baseline RAG pipeline.",
  },
];

export function Faq() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section id="faq" className="border-t py-20 sm:py-32">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <div className="text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Frequently Asked Questions
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Everything you need to know about SentinelRAG.
          </p>
        </div>

        <div className="mt-12 space-y-2">
          {faqs.map((faq, i) => (
            <div
              key={i}
              className="rounded-xl border bg-card overflow-hidden"
            >
              <button
                onClick={() => setOpenIndex(openIndex === i ? null : i)}
                className="flex w-full items-center justify-between gap-4 p-5 text-left transition-colors hover:bg-secondary/40"
              >
                <span className="font-medium text-sm">{faq.q}</span>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200",
                    openIndex === i && "rotate-180"
                  )}
                />
              </button>
              <AnimatePresence>
                {openIndex === i && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <p className="px-5 pb-5 text-sm text-muted-foreground leading-relaxed">
                      {faq.a}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
