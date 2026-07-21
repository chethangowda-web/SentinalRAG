"use client";

import { motion } from "framer-motion";

const stats = [
  { value: "94.7%", label: "Faithfulness" },
  { value: "70%", label: "Fewer Hallucinations" },
  { value: "86%", label: "Fewer Context Errors" },
  { value: "18/18", label: "Failure Tests Passed" },
];

export function Stats() {
  return (
    <section className="border-t py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Proven Performance
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Measured against a standard RAG baseline on an 18-question benchmark
            dataset covering factual, quantitative, and edge-case questions.
          </p>
        </div>

        <div className="mt-16 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, scale: 0.95 }}
              whileInView={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: i * 0.1 }}
              viewport={{ once: true }}
              className="text-center"
            >
              <div className="text-4xl font-bold tracking-tight text-primary sm:text-5xl">
                {stat.value}
              </div>
              <div className="mt-2 text-sm text-muted-foreground">{stat.label}</div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
