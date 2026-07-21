"use client";

import { motion } from "framer-motion";
import { Globe, Server, Database, Cpu, Shield } from "lucide-react";

const layers = [
  { icon: Globe, name: "Presentation", items: ["Next.js 15", "React 19", "TailwindCSS", "Framer Motion"] },
  { icon: Shield, name: "API Gateway", items: ["NGINX", "Rate Limiting", "Security Headers", "SSL"] },
  { icon: Server, name: "Application", items: ["FastAPI", "LangGraph", "Sentence Transformers", "Tesseract OCR"] },
  { icon: Database, name: "Data", items: ["PostgreSQL 16", "Qdrant", "Embeddings (384d)", "BM25 Index"] },
  { icon: Cpu, name: "Infrastructure", items: ["Docker Compose", "GitHub Actions", "Health Checks", "Metrics"] },
];

export function Architecture() {
  return (
    <section id="architecture" className="border-t py-20 sm:py-32 bg-secondary/20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Architecture
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            A modern, scalable stack designed for production RAG workloads.
          </p>
        </div>

        <div className="mt-16 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {layers.map((layer, i) => (
            <motion.div
              key={layer.name}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              viewport={{ once: true }}
              className="rounded-xl border bg-card p-5"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary mb-4">
                <layer.icon className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-sm mb-3">{layer.name}</h3>
              <ul className="space-y-1.5">
                {layer.items.map((item) => (
                  <li key={item} className="text-xs text-muted-foreground">
                    {item}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
